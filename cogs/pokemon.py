"""
cogs/pokemon.py — Full GBA-style Pokémon battle system for Mikasa Bot.
Registration, wild encounters, turn-based battles, catching, XP & leveling.
"""
import discord
from discord.ext import commands, tasks
import random
import asyncio

from supabase import create_client, Client, ClientOptions
import httpx
import config
import pokemon_data as pd

# ── Mikasa theme ──
MIKASA_COLOR = 0xE91E63
GOLD_COLOR   = 0xFFD700
MIKASA_ICON  = "https://i.imgur.com/0GfnTBq.png"

# ── Colors for type embeds ──
TYPE_COLORS = {
    "normal": 0xA8A878, "fire": 0xF08030, "water": 0x6890F0,
    "grass": 0x78C850,  "electric": 0xF8D030, "ice": 0x98D8D8,
    "fighting": 0xC03028,"poison": 0xA040A0, "ground": 0xE0C068,
    "flying": 0xA890F0, "psychic": 0xF85888, "bug": 0xA8B820,
    "rock": 0xB8A038,   "ghost": 0x705898, "dragon": 0x7038F8,
}

# XP needed to level up (simplified: 50 * level)
def xp_to_next_level(level: int) -> int:
    return 50 * level

# XP gained from winning a battle
def xp_from_battle(wild_level: int) -> int:
    return int(30 + wild_level * 2.5)


# ══════════════════════════════════════════════════════════════
#  BATTLE SESSION — holds the state of an ongoing fight
# ══════════════════════════════════════════════════════════════
class BattleSession:
    """Tracks all state for a single battle between a player and a wild Pokémon."""

    def __init__(self, player_id: int, player_pokemon: dict, wild_pokemon_id: int,
                 wild_level: int, wild_hp: int, wild_max_hp: int, wild_moves: list[str]):
        self.player_id = player_id
        self.pp = player_pokemon          # DB row dict
        self.wild_id = wild_pokemon_id
        self.wild_level = wild_level
        self.wild_hp = wild_hp
        self.wild_max_hp = wild_max_hp
        self.wild_moves = wild_moves
        self.wild_atk = pd.calc_stat(pd.KANTO_POKEMON[wild_pokemon_id]["atk"], wild_level)
        self.wild_def = pd.calc_stat(pd.KANTO_POKEMON[wild_pokemon_id]["def"], wild_level)
        self.wild_spd = pd.calc_stat(pd.KANTO_POKEMON[wild_pokemon_id]["spd"], wild_level)
        self.is_over = False
        self.message: discord.Message | None = None

    @property
    def wild_info(self):
        return pd.KANTO_POKEMON[self.wild_id]

    @property
    def player_info(self):
        return pd.KANTO_POKEMON[self.pp["pokemon_id"]]

    @property
    def player_atk(self):
        return pd.calc_stat(self.player_info["atk"], self.pp["level"])

    @property
    def player_def(self):
        return pd.calc_stat(self.player_info["def"], self.pp["level"])

    @property
    def player_spd(self):
        return pd.calc_stat(self.player_info["spd"], self.pp["level"])

    @property
    def player_max_hp(self):
        return pd.calc_hp(self.player_info["hp"], self.pp["level"])


# ══════════════════════════════════════════════════════════════
#  PVP SESSION — holds the state for a player-vs-player battle
# ══════════════════════════════════════════════════════════════
class PvPSession:
    """Tracks all state for a PvP battle between two trainers."""

    def __init__(self, p1_id: int, p1_pokemon: dict, p2_id: int, p2_pokemon: dict):
        self.p1_id = p1_id
        self.p1_pp = p1_pokemon                # DB row dict (copy)
        self.p1_info = pd.KANTO_POKEMON[p1_pokemon["pokemon_id"]]
        self.p1_hp = p1_pokemon["current_hp"]   # battle-local HP
        self.p1_max_hp = pd.calc_hp(self.p1_info["hp"], p1_pokemon["level"])
        self.p1_atk = pd.calc_stat(self.p1_info["atk"], p1_pokemon["level"])
        self.p1_def = pd.calc_stat(self.p1_info["def"], p1_pokemon["level"])
        self.p1_spd = pd.calc_stat(self.p1_info["spd"], p1_pokemon["level"])

        self.p2_id = p2_id
        self.p2_pp = p2_pokemon
        self.p2_info = pd.KANTO_POKEMON[p2_pokemon["pokemon_id"]]
        self.p2_hp = p2_pokemon["current_hp"]
        self.p2_max_hp = pd.calc_hp(self.p2_info["hp"], p2_pokemon["level"])
        self.p2_atk = pd.calc_stat(self.p2_info["atk"], p2_pokemon["level"])
        self.p2_def = pd.calc_stat(self.p2_info["def"], p2_pokemon["level"])
        self.p2_spd = pd.calc_stat(self.p2_info["spd"], p2_pokemon["level"])

        self.current_turn: int = p1_id  # whose turn it is
        self.p1_move: str | None = None
        self.p2_move: str | None = None
        self.is_over = False
        self.message: discord.Message | None = None


# ══════════════════════════════════════════════════════════════
#  BATTLE VIEW — move buttons + bag + run
# ══════════════════════════════════════════════════════════════
class BattleView(discord.ui.View):
    def __init__(self, cog: "PokemonCog", session: BattleSession):
        super().__init__(timeout=120)
        self.cog = cog
        self.session = session
        self._build_buttons()

    def _build_buttons(self):
        self.clear_items()
        moves = [self.session.pp.get(f"move_{i}") for i in range(1, 5)]
        moves = [m for m in moves if m]

        move_styles = [
            discord.ButtonStyle.primary,
            discord.ButtonStyle.primary,
            discord.ButtonStyle.primary,
            discord.ButtonStyle.primary,
        ]
        for idx, mv_key in enumerate(moves):
            mv = pd.MOVES.get(mv_key, {})
            label = mv.get("name", mv_key)
            t = mv.get("type", "normal")
            emoji = pd.TYPE_EMOJI.get(t, "⚪")
            btn = discord.ui.Button(
                label=label, emoji=emoji,
                style=move_styles[idx % 4],
                custom_id=f"move_{mv_key}",
                row=idx // 2,
            )
            btn.callback = self._make_move_callback(mv_key)
            self.add_item(btn)

        # Bag button
        bag_btn = discord.ui.Button(label="Bag", emoji="🎒", style=discord.ButtonStyle.secondary, row=2)
        bag_btn.callback = self._bag_callback
        self.add_item(bag_btn)

        # Run button
        run_btn = discord.ui.Button(label="Run", emoji="🏃", style=discord.ButtonStyle.danger, row=2)
        run_btn.callback = self._run_callback
        self.add_item(run_btn)

        # Switch button
        switch_btn = discord.ui.Button(label="Switch", emoji="🔄", style=discord.ButtonStyle.secondary, row=2)
        switch_btn.callback = self._switch_callback
        self.add_item(switch_btn)

    def _make_move_callback(self, move_key: str):
        async def callback(interaction: discord.Interaction):
            if interaction.user.id != self.session.player_id:
                await interaction.response.send_message("This isn't your battle! 😤", ephemeral=True)
                return
            if self.session.is_over:
                return
            await self.cog.execute_turn(interaction, self.session, move_key)
        return callback

    async def _bag_callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.session.player_id:
            await interaction.response.send_message("This isn't your battle! 😤", ephemeral=True)
            return
        if self.session.is_over:
            return
        await interaction.response.edit_message(
            view=BagView(self.cog, self.session)
        )

    async def _switch_callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.session.player_id:
            await interaction.response.send_message("This isn't your battle! 😤", ephemeral=True)
            return
        if self.session.is_over:
            return
        
        team_pokemon = self.cog._get_team(str(interaction.user.id))
        alive_team = [p for p in team_pokemon if p["id"] != self.session.pp["id"] and not p["is_fainted"]]
        
        if not alive_team:
            await interaction.response.send_message("You don't have any other Pokémon able to battle! 😅", ephemeral=True)
            return
            
        await interaction.response.edit_message(
            view=SwitchView(self.cog, self.session, None, interaction.user.id)
        )

    async def _run_callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.session.player_id:
            await interaction.response.send_message("This isn't your battle! 😤", ephemeral=True)
            return
        if self.session.is_over:
            return

        # 70% chance to escape, 30% denied
        if random.random() < 0.70:
            self.session.is_over = True
            embed = discord.Embed(
                title="🏃  Got Away Safely!",
                description=f"Phew! You got away safely! 😅",
                color=0x95A5A6,
            )
            embed.set_footer(text="Mikasa Pokémon", icon_url=MIKASA_ICON)
            self.cog.active_battles.pop(self.session.player_id, None)
            await interaction.response.edit_message(embed=embed, view=None)
        else:
            wild_name = self.session.wild_info["name"]
            embed = self.cog.build_battle_embed(self.session,
                log=f"🚫 **{wild_name}** blocked the escape! You have to fight! 😂")
            await interaction.response.edit_message(embed=embed, view=BattleView(self.cog, self.session))

    async def on_timeout(self):
        self.session.is_over = True
        self.cog.active_battles.pop(self.session.player_id, None)


# ══════════════════════════════════════════════════════════════
#  SWITCH VIEW — Select alive team member to switch in
# ══════════════════════════════════════════════════════════════
class SwitchView(discord.ui.View):
    def __init__(self, cog: "PokemonCog", wild_session: BattleSession | None, pvp_session: PvPSession | None, player_id: int):
        super().__init__(timeout=60)
        self.cog = cog
        self.wild_session = wild_session
        self.pvp_session = pvp_session
        self.player_id = player_id
        
        team = self.cog._get_team(str(player_id))
        current_id = None
        if wild_session:
            current_id = wild_session.pp["id"]
        elif pvp_session:
            current_id = pvp_session.p1_pp["id"] if pvp_session.p1_id == player_id else pvp_session.p2_pp["id"]
            
        alive_team = [p for p in team if p["id"] != current_id and not p["is_fainted"]]
        
        for pp in alive_team:
            info = pd.KANTO_POKEMON.get(pp["pokemon_id"], {})
            name = pp.get("nickname") or info.get("name", "???")
            max_hp = pd.calc_hp(info.get("hp", 1), pp["level"])
            emoji = pd.TYPE_EMOJI.get(info.get("types", ["normal"])[0], "⚪")
            
            btn = discord.ui.Button(
                label=f"{name} (Lv.{pp['level']}) [{pp['current_hp']}/{max_hp}]",
                emoji=emoji,
                style=discord.ButtonStyle.primary,
                custom_id=f"switch_{pp['id']}"
            )
            btn.callback = self._make_switch_callback(pp)
            self.add_item(btn)

        back_btn = discord.ui.Button(label="Back", emoji="↩️", style=discord.ButtonStyle.secondary)
        back_btn.callback = self._back_callback
        self.add_item(back_btn)

    def _make_switch_callback(self, new_pp: dict):
        async def callback(interaction: discord.Interaction):
            if interaction.user.id != self.player_id:
                await interaction.response.send_message("Not your choice to make! 😤", ephemeral=True)
                return
                
            info = pd.KANTO_POKEMON.get(new_pp["pokemon_id"], {})
            name = new_pp.get("nickname") or info.get("name", "???")
            log_msg = f"🔄 Come back! Go! **{name}**!"
            
            if self.wild_session:
                if self.wild_session.is_over: return
                self.wild_session.pp = new_pp
                self.wild_session.player_info = info
                self.wild_session.player_max_hp = pd.calc_hp(info.get("hp", 1), new_pp["level"])
                # The wild pokemon gets a free attack on the turn you switch (handled in execute_turn equivalent)
                await self.cog.execute_turn(interaction, self.wild_session, move_key="SWAPPED")
                
            elif self.pvp_session:
                if self.pvp_session.is_over: return
                s = self.pvp_session
                if s.p1_id == self.player_id:
                    s.p1_pp = new_pp
                    s.p1_info = info
                    s.p1_max_hp = pd.calc_hp(info.get("hp", 1), new_pp["level"])
                    s.p1_hp = new_pp["current_hp"]
                    s.p1_atk, s.p1_def, _, _ = pd.calc_stats(info, new_pp["level"])
                else:
                    s.p2_pp = new_pp
                    s.p2_info = info
                    s.p2_max_hp = pd.calc_hp(info.get("hp", 1), new_pp["level"])
                    s.p2_hp = new_pp["current_hp"]
                    s.p2_atk, s.p2_def, _, _ = pd.calc_stats(info, new_pp["level"])
                
                await self.cog.execute_pvp_turn(interaction, self.pvp_session, move_key="SWAPPED")

        return callback

    async def _back_callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.player_id: return
        if self.wild_session:
            embed = self.cog.build_battle_embed(self.wild_session)
            await interaction.response.edit_message(embed=embed, view=BattleView(self.cog, self.wild_session))
        elif self.pvp_session:
            s = self.pvp_session
            p1_member = interaction.guild.get_member(s.p1_id)
            p2_member = interaction.guild.get_member(s.p2_id)
            p1_name = p1_member.display_name if p1_member else "Trainer 1"
            p2_name = p2_member.display_name if p2_member else "Trainer 2"
            embed = self.cog.build_pvp_embed(s, p1_name, p2_name, turn_user_id=s.current_turn)
            await interaction.response.edit_message(embed=embed, view=PvPBattleView(self.cog, s))


# ══════════════════════════════════════════════════════════════
#  BAG VIEW — Pokéball + Potion + Super Potion
# ══════════════════════════════════════════════════════════════
class BagView(discord.ui.View):
    def __init__(self, cog: "PokemonCog", session: BattleSession):
        super().__init__(timeout=60)
        self.cog = cog
        self.session = session
        trainer = cog._get_trainer(str(session.player_id))
        balls = trainer.get("pokeballs", 0) if trainer else 0
        pots = trainer.get("potions", 0) if trainer else 0
        s_pots = trainer.get("super_potions", 0) if trainer else 0

        ball_btn = discord.ui.Button(
            label=f"Pokéball ({balls})", emoji="<:pokeball:1479372175239544973>",
            style=discord.ButtonStyle.primary,
            disabled=(balls <= 0),
        )
        ball_btn.callback = self._pokeball_callback
        self.add_item(ball_btn)

        pot_btn = discord.ui.Button(
            label=f"Potion ({pots})", emoji="💊",
            style=discord.ButtonStyle.success,
            disabled=(pots <= 0),
        )
        pot_btn.callback = self._potion_callback
        self.add_item(pot_btn)

        spot_btn = discord.ui.Button(
            label=f"Super Potion ({s_pots})", emoji="💉",
            style=discord.ButtonStyle.success,
            disabled=(s_pots <= 0),
        )
        spot_btn.callback = self._super_potion_callback
        self.add_item(spot_btn)

        back_btn = discord.ui.Button(label="Back", emoji="↩️", style=discord.ButtonStyle.secondary)
        back_btn.callback = self._back_callback
        self.add_item(back_btn)

    async def _pokeball_callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.session.player_id:
            await interaction.response.send_message("This isn't your bag! 😤", ephemeral=True)
            return
        await self.cog.throw_pokeball(interaction, self.session)

    async def _potion_callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.session.player_id:
            await interaction.response.send_message("This isn't your bag! 😤", ephemeral=True)
            return
        await self.cog.use_potion(interaction, self.session)

    async def _super_potion_callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.session.player_id:
            await interaction.response.send_message("This isn't your bag! 😤", ephemeral=True)
            return
        await self.cog.use_super_potion(interaction, self.session)

    async def _back_callback(self, interaction: discord.Interaction):
        embed = self.cog.build_battle_embed(self.session)
        await interaction.response.edit_message(embed=embed, view=BattleView(self.cog, self.session))


# ══════════════════════════════════════════════════════════════
#  WILD ENCOUNTER VIEW — Battle / Run
# ══════════════════════════════════════════════════════════════
class WildEncounterView(discord.ui.View):
    def __init__(self, cog: "PokemonCog", wild_id: int, wild_level: int):
        super().__init__(timeout=180)
        self.cog = cog
        self.wild_id = wild_id
        self.wild_level = wild_level
        self.claimed = False

    @discord.ui.button(label="Battle", emoji="⚔️", style=discord.ButtonStyle.danger)
    async def battle_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.claimed:
            await interaction.response.send_message("Someone is already battling this Pokémon! 😅", ephemeral=True)
            return

        user_id = str(interaction.user.id)
        trainer = self.cog._get_trainer(user_id)
        if not trainer:
            await interaction.response.send_message(
                "You're not registered yet! Use `Mikasa pokestart` first! 🎮", ephemeral=True)
            return

        lead = self.cog._get_lead_pokemon(user_id)
        if not lead:
            await interaction.response.send_message(
                "You don't have any Pokémon! 😱", ephemeral=True)
            return
        if lead.get("is_fainted", False):
            await interaction.response.send_message(
                "Your lead Pokémon has fainted! Heal it with a Potion first! 💊", ephemeral=True)
            return

        self.claimed = True
        # Disable both buttons
        for item in self.children:
            item.disabled = True

        # Scale wild level to this player's top Pokémon, max level 12
        top_level = self.cog._get_top_level(user_id)
        scaled_level = random.randint(max(3, top_level - 15), top_level + 5)
        scaled_level = min(scaled_level, 12)
        wild_max_hp = pd.calc_hp(pd.KANTO_POKEMON[self.wild_id]["hp"], scaled_level)
        wild_moves = pd.get_moves_at_level(self.wild_id, scaled_level)
        if not wild_moves:
            wild_moves = ["tackle"]

        session = BattleSession(
            player_id=interaction.user.id,
            player_pokemon=lead,
            wild_pokemon_id=self.wild_id,
            wild_level=scaled_level,
            wild_hp=wild_max_hp,
            wild_max_hp=wild_max_hp,
            wild_moves=wild_moves,
        )
        self.cog.active_battles[interaction.user.id] = session

        # Update the spawn message
        wild_name = pd.KANTO_POKEMON[self.wild_id]["name"]
        spawn_embed = discord.Embed(
            title=f"⚔️  {interaction.user.display_name} is battling wild {wild_name}!",
            color=0x95A5A6,
        )
        spawn_embed.set_footer(text="Mikasa Pokémon", icon_url=MIKASA_ICON)
        await interaction.response.edit_message(embed=spawn_embed, view=self)

        # Send the battle embed
        embed = self.cog.build_battle_embed(session,
            log=f"🌿 A wild **{wild_name}** (Lv.{scaled_level}) appeared! What will you do? 👀")
        msg = await interaction.followup.send(embed=embed, view=BattleView(self.cog, session))
        session.message = msg

    @discord.ui.button(label="Run", emoji="🏃", style=discord.ButtonStyle.secondary)
    async def run_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.claimed:
            await interaction.response.send_message("Someone else is already battling! 😅", ephemeral=True)
            return

        self.claimed = True
        for item in self.children:
            item.disabled = True

        wild_name = pd.KANTO_POKEMON[self.wild_id]["name"]

        # 80% chance to run, 20% wild blocks and forces battle
        if random.random() < 0.80:
            embed = discord.Embed(
                title="🏃  Ran Away!",
                description=f"**{interaction.user.display_name}** ran from **{wild_name}**!",
                color=0x95A5A6,
            )
            embed.set_footer(text="Mikasa Pokémon", icon_url=MIKASA_ICON)
            await interaction.response.edit_message(embed=embed, view=self)
            if hasattr(self, '_guild_id'):
                self.cog.encounter_active.pop(self._guild_id, None)
        else:
            # Run denied — force battle
            self.claimed = False
            for item in self.children:
                item.disabled = False
            # only disable Run
            self.children[1].disabled = True

            embed = discord.Embed(
                title=f"🌿  Wild {wild_name} appeared!  (Lv. ???)",
                description=(
                    f"**{wild_name}** blocked your escape! 😂\n"
                    f"*\"Not so fast! You'll have to fight!\"*\n\n"
                    f"Click **⚔️ Battle** to fight!"
                ),
                color=TYPE_COLORS.get(pd.KANTO_POKEMON[self.wild_id]["types"][0], MIKASA_COLOR),
            )
            embed.set_thumbnail(url=pd.get_sprite_url(self.wild_id))
            embed.set_footer(text="Mikasa Pokémon", icon_url=MIKASA_ICON)
            await interaction.response.edit_message(embed=embed, view=self)

    async def on_timeout(self):
        # Disable buttons and edit the message to show it expired
        for item in self.children:
            item.disabled = True
        if hasattr(self, '_guild_id'):
            self.cog.encounter_active.pop(self._guild_id, None)
        # Try to edit the message to show expired state
        try:
            embed = discord.Embed(
                title="🌿  The wild Pokémon fled!",
                description="No one battled in time... The wild Pokémon ran away! 🏃💨",
                color=0x95A5A6,
            )
            embed.set_footer(text="Mikasa Pokémon", icon_url=MIKASA_ICON)
            if self.message:
                await self.message.edit(embed=embed, view=None)
        except Exception:
            pass


# ══════════════════════════════════════════════════════════════
#  MAIN COG
# ══════════════════════════════════════════════════════════════
class PokemonCog(commands.Cog, name="Pokemon"):
    """GBA-style Pokémon battle system with wild encounters, battles, and catching!"""

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        
        # We pass a custom httpx Client to disable HTTP/2 and set short keepalive
        # since Supabase idle connections get dropped by the server and cause httpx.RemoteProtocolError
        http_client = httpx.Client(
            http2=False,
            limits=httpx.Limits(max_keepalive_connections=5, keepalive_expiry=5.0)
        )
        opts = ClientOptions(httpx_client=http_client)
        self.db: Client = create_client(config.SUPABASE_URL, config.SUPABASE_KEY, options=opts)
        
        self.active_battles: dict[int, BattleSession] = {}
        self.active_pvp: dict[int, PvPSession] = {}   # player_id → PvPSession
        # Track active encounters per guild so multiple servers can run independently
        self.encounter_active: dict[int, bool] = {}  # guild_id → bool

    async def cog_load(self):
        self.wild_spawn_loop.start()

    async def cog_unload(self):
        self.wild_spawn_loop.cancel()

    # ── Spawn Channel DB Helpers ──────────────────────────────

    def _get_spawn_channels(self) -> list[dict]:
        """Get all active spawn channel configs from the DB."""
        res = self.db.table("pokemon_spawns").select("*").eq("is_active", True).execute()
        return res.data

    def _get_spawn_channel(self, guild_id: str) -> dict | None:
        res = self.db.table("pokemon_spawns").select("*").eq("guild_id", guild_id).execute()
        return res.data[0] if res.data else None

    def _set_spawn_channel(self, guild_id: str, channel_id: str):
        self.db.table("pokemon_spawns").upsert({
            "guild_id": guild_id,
            "channel_id": channel_id,
            "is_active": True,
        }).execute()

    def _stop_spawn_channel(self, guild_id: str):
        self.db.table("pokemon_spawns").update({
            "is_active": False,
        }).eq("guild_id", guild_id).execute()

    # ── DB Helpers ────────────────────────────────────────────

    def _get_trainer(self, user_id: str) -> dict | None:
        res = self.db.table("trainers").select("*").eq("user_id", user_id).execute()
        return res.data[0] if res.data else None

    def _register_trainer(self, user_id: str, nickname: str):
        self.db.table("trainers").insert({
            "user_id": user_id,
            "nickname": nickname,
        }).execute()

    def _get_team(self, user_id: str) -> list[dict]:
        """Get active team (slots 1-5, not fainted)."""
        res = (self.db.table("player_pokemon")
               .select("*")
               .eq("user_id", user_id)
               .eq("is_fainted", False)
               .gt("slot", 0)
               .lte("slot", 5)
               .order("slot")
               .execute())
        return res.data

    def _get_all_pokemon(self, user_id: str) -> list[dict]:
        """Get all Pokémon (team + storage)."""
        res = (self.db.table("player_pokemon")
               .select("*")
               .eq("user_id", user_id)
               .order("slot")
               .execute())
        return res.data

    def _get_team_pokemon(self, user_id: str) -> list[dict]:
        """Get active team (slots 1-5, including fainted)."""
        res = (self.db.table("player_pokemon")
               .select("*")
               .eq("user_id", user_id)
               .gt("slot", 0)
               .lte("slot", 5)
               .order("slot")
               .execute())
        return res.data

    def _get_stored_pokemon(self, user_id: str) -> list[dict]:
        """Get Pokémon in PokéMachine (slot=0)."""
        res = (self.db.table("player_pokemon")
               .select("*")
               .eq("user_id", user_id)
               .eq("slot", 0)
               .order("id")
               .execute())
        return res.data

    def _get_lead_pokemon(self, user_id: str) -> dict | None:
        res = (self.db.table("player_pokemon")
               .select("*")
               .eq("user_id", user_id)
               .gt("slot", 0)
               .lte("slot", 5)
               .order("slot")
               .limit(1)
               .execute())
        return res.data[0] if res.data else None

    def _get_top_level(self, user_id: str) -> int:
        res = (self.db.table("player_pokemon")
               .select("level")
               .eq("user_id", user_id)
               .order("level", desc=True)
               .limit(1)
               .execute())
        return res.data[0]["level"] if res.data else 5

    def _add_pokemon(self, user_id: str, pokemon_id: int, level: int, slot: int):
        moves = pd.get_moves_at_level(pokemon_id, level)
        max_hp = pd.calc_hp(pd.KANTO_POKEMON[pokemon_id]["hp"], level)
        data = {
            "user_id": user_id,
            "pokemon_id": pokemon_id,
            "level": level,
            "xp": 0,
            "current_hp": max_hp,
            "move_1": moves[0] if len(moves) > 0 else "tackle",
            "move_2": moves[1] if len(moves) > 1 else None,
            "move_3": moves[2] if len(moves) > 2 else None,
            "move_4": moves[3] if len(moves) > 3 else None,
            "is_fainted": False,
            "slot": slot,
        }
        self.db.table("player_pokemon").insert(data).execute()

    def _update_pokemon_hp(self, pp_id: int, hp: int, fainted: bool = False):
        self.db.table("player_pokemon").update({
            "current_hp": max(hp, 0),
            "is_fainted": fainted,
        }).eq("id", pp_id).execute()

    def _update_pokemon_xp(self, pp_id: int, xp: int, level: int, moves: dict):
        data = {"xp": xp, "level": level}
        data.update(moves)
        self.db.table("player_pokemon").update(data).eq("id", pp_id).execute()

    def _update_trainer_items(self, user_id: str, **items):
        self.db.table("trainers").update(items).eq("user_id", user_id).execute()

    # ── Battle Embed Builder ──────────────────────────────────

    def build_battle_embed(self, s: BattleSession, log: str = "") -> discord.Embed:
        p_info = s.player_info
        w_info = s.wild_info
        p_types = pd.format_types(p_info["types"])
        w_types = pd.format_types(w_info["types"])
        p_max_hp = s.player_max_hp
        p_hp = s.pp["current_hp"]
        p_bar = pd.render_hp_bar(p_hp, p_max_hp)
        w_bar = pd.render_hp_bar(s.wild_hp, s.wild_max_hp)

        poke_name = s.pp.get("nickname") or p_info["name"]

        embed = discord.Embed(
            title="⚔️  Pokémon Battle!",
            color=TYPE_COLORS.get(p_info["types"][0], MIKASA_COLOR),
        )

        # Player's Pokémon as author (top-left icon)
        embed.set_author(
            name=f"{poke_name}  •  Lv.{s.pp['level']}",
            icon_url=pd.get_sprite_url(s.pp["pokemon_id"]),
        )

        # Wild Pokémon sprite as thumbnail (top-right)
        embed.set_thumbnail(url=pd.get_sprite_url(s.wild_id))

        # Wild Pokémon (top section)
        embed.add_field(
            name=f"🌿 Wild {w_info['name']}  •  Lv.{s.wild_level}",
            value=f"{w_types}\n{w_bar}\n`HP: {s.wild_hp}/{s.wild_max_hp}`",
            inline=True,
        )

        # Separator (Takes up minimal space when placed between two inlines if Discord permits, or pushes the next line)
        embed.add_field(name="⚔️  VS  ⚔️", value=" \n \n ", inline=True)

        # Player's Pokémon (horizontally stacked)
        embed.add_field(
            name=f"🔴 {poke_name}  •  Lv.{s.pp['level']}",
            value=f"{p_types}\n{p_bar}\n`HP: {p_hp}/{p_max_hp}`",
            inline=True,
        )

        if log:
            embed.add_field(name="📜 Battle Log", value=log, inline=False)

        embed.set_footer(text="Pick a move to attack!", icon_url=MIKASA_ICON)
        return embed

    # ── Battle Logic ──────────────────────────────────────────

    async def execute_turn(self, interaction: discord.Interaction,
                           session: BattleSession, player_move_key: str):
        """Execute a full turn: player attacks, then wild attacks."""
        s = session
        p_info = s.player_info
        w_info = s.wild_info
        p_move = pd.MOVES.get(player_move_key, pd.MOVES["tackle"])
        log_lines = []

        # Determine turn order by speed
        player_first = s.player_spd >= s.wild_spd

        async def player_attack():
            """Player's attack phase."""
            eff = pd.get_type_effectiveness(p_move["type"], w_info["types"])
            stab = p_move["type"] in p_info["types"]
            dmg = pd.calc_damage(s.pp["level"], p_move["power"], s.player_atk, s.wild_def, eff, stab)
            s.wild_hp = max(0, s.wild_hp - dmg)

            poke_name = s.pp.get("nickname") or p_info["name"]
            line = f"🔴 **{poke_name}** used **{p_move['name']}**! (-{dmg} HP)"
            if eff > 1.0:
                line += "\n🔥 *It's super effective!*"
            elif eff < 1.0 and eff > 0:
                line += "\n😅 *Not very effective...*"
            elif eff == 0:
                line += "\n🚫 *It had no effect!*"
            if stab:
                line += " *(STAB)*"
            log_lines.append(line)

        async def wild_attack():
            """Wild Pokémon's attack phase."""
            w_move_key = random.choice(s.wild_moves)
            w_move = pd.MOVES.get(w_move_key, pd.MOVES["tackle"])
            eff = pd.get_type_effectiveness(w_move["type"], p_info["types"])
            stab = w_move["type"] in w_info["types"]
            dmg = pd.calc_damage(s.wild_level, w_move["power"], s.wild_atk, s.player_def, eff, stab)
            s.pp["current_hp"] = max(0, s.pp["current_hp"] - dmg)

            line = f"🌿 Wild **{w_info['name']}** used **{w_move['name']}**! (-{dmg} HP)"
            if eff > 1.0:
                line += "\n🔥 *It's super effective!*"
            elif eff < 1.0 and eff > 0:
                line += "\n😅 *Not very effective...*"
            elif eff == 0:
                line += "\n🚫 *It had no effect!*"
            log_lines.append(line)

        # Execute turn order
        if player_first:
            await player_attack()
            if s.wild_hp > 0:
                await wild_attack()
        else:
            await wild_attack()
            if s.pp["current_hp"] > 0:
                await player_attack()

        log = "\n".join(log_lines)

        # Check if wild fainted
        if s.wild_hp <= 0:
            s.is_over = True
            self.active_battles.pop(s.player_id, None)
            self._update_pokemon_hp(s.pp["id"], s.pp["current_hp"])

            # Grant XP
            gained_xp = xp_from_battle(s.wild_level)
            new_xp = s.pp["xp"] + gained_xp
            new_level = s.pp["level"]
            level_up_msg = ""

            while new_xp >= xp_to_next_level(new_level):
                new_xp -= xp_to_next_level(new_level)
                new_level += 1
                level_up_msg += f"\n🎉 **{p_info['name']}** grew to **Lv. {new_level}**!"

            # Check for new moves at new level
            new_moves = pd.get_moves_at_level(s.pp["pokemon_id"], new_level)
            move_data = {
                "move_1": new_moves[0] if len(new_moves) > 0 else s.pp["move_1"],
                "move_2": new_moves[1] if len(new_moves) > 1 else s.pp.get("move_2"),
                "move_3": new_moves[2] if len(new_moves) > 2 else s.pp.get("move_3"),
                "move_4": new_moves[3] if len(new_moves) > 3 else s.pp.get("move_4"),
            }
            self._update_pokemon_xp(s.pp["id"], new_xp, new_level, move_data)

            # Check evolution
            evo_msg = ""
            evo = p_info.get("evo")
            if evo and new_level >= evo[1]:
                evo_target = evo[0]
                evo_info = pd.KANTO_POKEMON[evo_target]
                evo_max_hp = pd.calc_hp(evo_info["hp"], new_level)
                evo_moves = pd.get_moves_at_level(evo_target, new_level)
                evo_data = {
                    "pokemon_id": evo_target,
                    "level": new_level,
                    "xp": new_xp,
                    "current_hp": evo_max_hp,
                    "move_1": evo_moves[0] if len(evo_moves) > 0 else "tackle",
                    "move_2": evo_moves[1] if len(evo_moves) > 1 else None,
                    "move_3": evo_moves[2] if len(evo_moves) > 2 else None,
                    "move_4": evo_moves[3] if len(evo_moves) > 3 else None,
                }
                self.db.table("player_pokemon").update(evo_data).eq("id", s.pp["id"]).execute()
                evo_msg = f"\n\n✨ **Wait... What's happening?!**\n🌟 **{p_info['name']}** is evolving into **{evo_info['name']}**! 🌟"

            embed = discord.Embed(
                title="🏆  Victory!",
                description=(
                    f"{log}\n\n"
                    f"🌿 Wild **{w_info['name']}** fainted!\n"
                    f"⭐ Gained **{gained_xp} XP**!{level_up_msg}{evo_msg}"
                ),
                color=0x2ECC71,
            )
            embed.set_thumbnail(url=pd.get_sprite_url(s.pp["pokemon_id"]))
            embed.set_footer(text="Mikasa Pokémon", icon_url=MIKASA_ICON)
            await interaction.response.edit_message(embed=embed, view=None)
            return

        # Check if player's Pokémon fainted
        if s.pp["current_hp"] <= 0:
            self._update_pokemon_hp(s.pp["id"], 0, fainted=True)
            
            # Check if player has other living team members
            team_pokemon = self._get_team(str(s.player_id))
            alive_team = [p for p in team_pokemon if p["id"] != s.pp["id"] and not p["is_fainted"]]
            
            if alive_team:
                embed = discord.Embed(
                    title="💀  Pokémon Fainted!",
                    description=(
                        f"{log}\n\n"
                        f"😢 **{p_info['name']}** fainted!\n"
                        f"Choose another Pokémon to send out! 👇"
                    ),
                    color=0xE74C3C,
                )
                embed.set_thumbnail(url=pd.get_sprite_url(s.wild_id))
                embed.set_footer(text="Mikasa Pokémon", icon_url=MIKASA_ICON)
                
                # We do NOT pop s.player_id from active_battles, they are still in the battle
                # We present the SwitchView to force them to pick a new Pokémon
                await interaction.response.edit_message(embed=embed, view=SwitchView(self, s, None, s.player_id))
                return
            else:
                # White out
                s.is_over = True
                self.active_battles.pop(s.player_id, None)

                embed = discord.Embed(
                    title="💀  Defeat...",
                    description=(
                        f"{log}\n\n"
                        f"😢 **{p_info['name']}** fainted!\n"
                        f"You have no more usable Pokémon!\n"
                        f"**{interaction.user.display_name}** blacked out! 😵"
                    ),
                    color=0xE74C3C,
                )
                embed.set_thumbnail(url=pd.get_sprite_url(s.wild_id))
                embed.set_footer(text="Mikasa Pokémon", icon_url=MIKASA_ICON)
                await interaction.response.edit_message(embed=embed, view=None)
                return

        # Battle continues — update HP in DB and show next turn
        self._update_pokemon_hp(s.pp["id"], s.pp["current_hp"])
        embed = self.build_battle_embed(s, log=log)
        await interaction.response.edit_message(embed=embed, view=BattleView(self, s))

    # ── Pokéball Logic ────────────────────────────────────────

    async def throw_pokeball(self, interaction: discord.Interaction, s: BattleSession):
        trainer = self._get_trainer(str(s.player_id))
        if not trainer or trainer["pokeballs"] <= 0:
            await interaction.response.send_message("You're out of Pokéballs! Visit the PokéMart! 🏪", ephemeral=True)
            return

        # Use one ball
        self._update_trainer_items(str(s.player_id), pokeballs=trainer["pokeballs"] - 1)
        catch_rate = pd.get_catch_rate(s.wild_hp, s.wild_max_hp)
        caught = random.random() < catch_rate

        w_info = s.wild_info
        if caught:
            s.is_over = True
            self.active_battles.pop(s.player_id, None)

            # Add to team or PokéMachine
            team = self._get_team_pokemon(str(s.player_id))
            if len(team) < 5:
                new_slot = len(team) + 1
                destination = f"📍 Added to your team as Slot #{new_slot}"
            else:
                new_slot = 0  # PokéMachine
                destination = "📦 Your team is full! Sent to **PokéMachine** for storage."

            wild_moves = pd.get_moves_at_level(s.wild_id, s.wild_level)
            data = {
                "user_id": str(s.player_id),
                "pokemon_id": s.wild_id,
                "level": s.wild_level,
                "xp": 0,
                "current_hp": s.wild_hp,
                "move_1": wild_moves[0] if len(wild_moves) > 0 else "tackle",
                "move_2": wild_moves[1] if len(wild_moves) > 1 else None,
                "move_3": wild_moves[2] if len(wild_moves) > 2 else None,
                "move_4": wild_moves[3] if len(wild_moves) > 3 else None,
                "is_fainted": False,
                "slot": new_slot,
            }
            self.db.table("player_pokemon").insert(data).execute()

            embed = discord.Embed(
                title="🎉  Gotcha!",
                description=(
                    f"**{w_info['name']}** (Lv.{s.wild_level}) was caught! 🔴\n\n"
                    f"*Excellent catch, Trainer!* ✨\n\n"
                    f"{destination}"
                ),
                color=GOLD_COLOR,
            )
            embed.set_thumbnail(url=pd.get_sprite_url(s.wild_id))
            embed.set_footer(text="Mikasa Pokémon", icon_url=MIKASA_ICON)
            await interaction.response.edit_message(embed=embed, view=None)
        else:
            # Failed catch — wild Pokémon attacks!
            w_move_key = random.choice(s.wild_moves)
            w_move = pd.MOVES.get(w_move_key, pd.MOVES["tackle"])
            p_info = s.player_info
            eff = pd.get_type_effectiveness(w_move["type"], p_info["types"])
            stab = w_move["type"] in w_info["types"]
            dmg = pd.calc_damage(s.wild_level, w_move["power"], s.wild_atk, s.player_def, eff, stab)
            s.pp["current_hp"] = max(0, s.pp["current_hp"] - dmg)
            self._update_pokemon_hp(s.pp["id"], s.pp["current_hp"],
                                     fainted=(s.pp["current_hp"] <= 0))

            pct = int(catch_rate * 100)
            log = (
                f"<:pokeball:1479372175239544973> You threw a **Pokéball**! ({pct}% chance)\n"
                f"😤 *Argh! Almost had it!* It broke free!\n\n"
                f"🌿 Wild **{w_info['name']}** used **{w_move['name']}**! (-{dmg} HP)"
            )

            if s.pp["current_hp"] <= 0:
                s.is_over = True
                self.active_battles.pop(s.player_id, None)
                embed = discord.Embed(
                    title="💀  Defeat...",
                    description=f"{log}\n\n😢 **{p_info['name']}** fainted!",
                    color=0xE74C3C,
                )
                embed.set_footer(text="Mikasa Pokémon", icon_url=MIKASA_ICON)
                await interaction.response.edit_message(embed=embed, view=None)
            else:
                embed = self.build_battle_embed(s, log=log)
                await interaction.response.edit_message(embed=embed, view=BattleView(self, s))

    # ── Potion Logic ──────────────────────────────────────────

    async def use_potion(self, interaction: discord.Interaction, s: BattleSession):
        trainer = self._get_trainer(str(s.player_id))
        if not trainer or trainer["potions"] <= 0:
            await interaction.response.send_message("You're out of Potions! Visit the PokéMart! 🏪", ephemeral=True)
            return

        self._update_trainer_items(str(s.player_id), potions=trainer["potions"] - 1)
        max_hp = s.player_max_hp
        heal = int(max_hp * 0.4)  # Potion heals 40% of max HP
        s.pp["current_hp"] = min(max_hp, s.pp["current_hp"] + heal)
        self._update_pokemon_hp(s.pp["id"], s.pp["current_hp"])

        # Wild Pokémon attacks after potion use
        w_move_key = random.choice(s.wild_moves)
        w_move = pd.MOVES.get(w_move_key, pd.MOVES["tackle"])
        w_info = s.wild_info
        p_info = s.player_info
        eff = pd.get_type_effectiveness(w_move["type"], p_info["types"])
        stab = w_move["type"] in w_info["types"]
        dmg = pd.calc_damage(s.wild_level, w_move["power"], s.wild_atk, s.player_def, eff, stab)
        s.pp["current_hp"] = max(0, s.pp["current_hp"] - dmg)
        self._update_pokemon_hp(s.pp["id"], s.pp["current_hp"],
                                 fainted=(s.pp["current_hp"] <= 0))

        poke_name = s.pp.get("nickname") or p_info["name"]
        log = (
            f"💊 **{poke_name}** recovered **+{heal} HP**!\n\n"
            f"🌿 Wild **{w_info['name']}** used **{w_move['name']}**! (-{dmg} HP)"
        )

        if s.pp["current_hp"] <= 0:
            s.is_over = True
            self.active_battles.pop(s.player_id, None)
            embed = discord.Embed(
                title="💀  Defeat...",
                description=f"{log}\n\n😢 **{poke_name}** fainted!",
                color=0xE74C3C,
            )
            embed.set_footer(text="Mikasa Pokémon", icon_url=MIKASA_ICON)
            await interaction.response.edit_message(embed=embed, view=None)
        else:
            embed = self.build_battle_embed(s, log=log)
            await interaction.response.edit_message(embed=embed, view=BattleView(self, s))

    async def use_super_potion(self, interaction: discord.Interaction, s: BattleSession):
        trainer = self._get_trainer(str(s.player_id))
        if not trainer or trainer.get("super_potions", 0) <= 0:
            await interaction.response.send_message("You're out of Super Potions! Visit the PokéMart! 🏪", ephemeral=True)
            return

        self._update_trainer_items(str(s.player_id), super_potions=trainer["super_potions"] - 1)
        max_hp = s.player_max_hp
        heal = max_hp - s.pp["current_hp"]
        s.pp["current_hp"] = max_hp
        self._update_pokemon_hp(s.pp["id"], s.pp["current_hp"])

        # Wild Pokémon attacks after super potion use
        w_move_key = random.choice(s.wild_moves)
        w_move = pd.MOVES.get(w_move_key, pd.MOVES["tackle"])
        w_info = s.wild_info
        p_info = s.player_info
        eff = pd.get_type_effectiveness(w_move["type"], p_info["types"])
        stab = w_move["type"] in w_info["types"]
        dmg = pd.calc_damage(s.wild_level, w_move["power"], s.wild_atk, s.player_def, eff, stab)
        s.pp["current_hp"] = max(0, s.pp["current_hp"] - dmg)
        self._update_pokemon_hp(s.pp["id"], s.pp["current_hp"],
                                 fainted=(s.pp["current_hp"] <= 0))

        poke_name = s.pp.get("nickname") or p_info["name"]
        log = (
            f"💉 **{poke_name}** fully healed to **{max_hp} HP**!\n\n"
            f"🌿 Wild **{w_info['name']}** used **{w_move['name']}**! (-{dmg} HP)"
        )

        if s.pp["current_hp"] <= 0:
            s.is_over = True
            self.active_battles.pop(s.player_id, None)
            embed = discord.Embed(
                title="💀  Defeat...",
                description=f"{log}\n\n😢 **{poke_name}** fainted!",
                color=0xE74C3C,
            )
            embed.set_footer(text="Mikasa Pokémon", icon_url=MIKASA_ICON)
            await interaction.response.edit_message(embed=embed, view=None)
        else:
            embed = self.build_battle_embed(s, log=log)
            await interaction.response.edit_message(embed=embed, view=BattleView(self, s))

    # ── Wild Spawn Loop ───────────────────────────────────────

    @tasks.loop(minutes=3)
    async def wild_spawn_loop(self):
        """Spawn a wild Pokémon in every active guild's designated channel."""
        spawn_configs = self._get_spawn_channels()
        for cfg in spawn_configs:
            guild_id = int(cfg["guild_id"])
            channel_id = int(cfg["channel_id"])

            # Skip if there's already an active encounter in this guild
            if self.encounter_active.get(guild_id, False):
                continue

            channel = self.bot.get_channel(channel_id)
            if not channel:
                continue

            # Pick a random wild Pokémon
            wild_ids = pd.get_wild_pokemon_ids()
            wild_id = random.choice(wild_ids)
            w_info = pd.KANTO_POKEMON[wild_id]
            w_types = pd.format_types(w_info["types"])

            self.encounter_active[guild_id] = True

            embed = discord.Embed(
                title=f"🌿  A wild {w_info['name']} appeared!",
                description=(
                    f"{w_types}\n\n"
                    f"*A wild {w_info['name']} has appeared!* 🌟\n\n"
                    f"⚔️ **Battle** to fight  |  🏃 **Run** to flee"
                ),
                color=TYPE_COLORS.get(w_info["types"][0], MIKASA_COLOR),
            )
            embed.set_image(url=pd.get_sprite_url(wild_id))
            embed.set_footer(text="Mikasa Pokémon  •  Click a button!", icon_url=MIKASA_ICON)

            view = WildEncounterView(self, wild_id, 5)
            view._guild_id = guild_id  # Tag view so timeout can clean up per-guild
            msg = await channel.send(embed=embed, view=view)
            view.message = msg  # Store for on_timeout editing

    @wild_spawn_loop.before_loop
    async def before_spawn(self):
        await self.bot.wait_until_ready()

    # ── Admin: Spawn Channel Setup ────────────────────────────

    @commands.group(name="pokemon", invoke_without_command=True)
    async def pokemon_group(self, ctx: commands.Context):
        """Pokémon admin commands. Use `Mikasa pokemon spawn` or `Mikasa pokemon stop`."""
        await ctx.send(embed=discord.Embed(
            description=(
                "🔴 **Pokémon Admin Commands:**\n\n"
                "▸ `Mikasa pokemon spawn` — Set this channel for wild Pokémon spawns\n"
                "▸ `Mikasa pokemon stop` — Stop wild Pokémon spawns in this server"
            ),
            color=MIKASA_COLOR,
        ))

    @pokemon_group.command(name="spawn")
    @commands.has_permissions(manage_channels=True)
    async def pokemon_spawn(self, ctx: commands.Context):
        """Set the current channel as the wild Pokémon spawn channel for this server."""
        guild_id = str(ctx.guild.id)
        channel_id = str(ctx.channel.id)
        self._set_spawn_channel(guild_id, channel_id)

        embed = discord.Embed(
            title="🌿  Wild Pokémon Spawns Activated!",
            description=(
                f"This channel ({ctx.channel.mention}) is now the **Wild Pokémon Zone**! 🎉\n\n"
                f"Wild Pokémon will appear here every **3-5 minutes**.\n"
                f"Make sure trainers are registered with `Mikasa pokestart`!\n\n"
                f"*Wild Pokémon are now roaming this channel!* ✨"
            ),
            color=0x2ECC71,
        )
        embed.set_footer(text="Mikasa Pokémon  •  Admin command", icon_url=MIKASA_ICON)
        await ctx.send(embed=embed)

    @pokemon_group.command(name="stop")
    @commands.has_permissions(manage_channels=True)
    async def pokemon_stop(self, ctx: commands.Context):
        """Stop wild Pokémon spawns in this server."""
        guild_id = str(ctx.guild.id)
        existing = self._get_spawn_channel(guild_id)
        if not existing or not existing.get("is_active"):
            await ctx.send(embed=discord.Embed(
                description="Spawns are already off in this server! 🤷", color=0xFF0000))
            return

        self._stop_spawn_channel(guild_id)
        self.encounter_active.pop(int(guild_id), None)

        embed = discord.Embed(
            title="🛑  Wild Pokémon Spawns Stopped",
            description=(
                f"Wild Pokémon will no longer spawn in this server.\n"
                f"Use `Mikasa pokemon spawn` in any channel to start again!\n\n"
                f"*Spawning has been disabled for this server.* 😎"
            ),
            color=0xE74C3C,
        )
        embed.set_footer(text="Mikasa Pokémon  •  Admin command", icon_url=MIKASA_ICON)
        await ctx.send(embed=embed)

    @pokemon_spawn.error
    @pokemon_stop.error
    async def spawn_error(self, ctx: commands.Context, error):
        if isinstance(error, commands.MissingPermissions):
            await ctx.send(embed=discord.Embed(
                description="❌ Only admins with Manage Channels permission can use this command!",
                color=0xFF0000,
            ))

    # ── Commands ──────────────────────────────────────────────

    @commands.command(name="pokestart")
    async def register(self, ctx: commands.Context):
        """Register as a Pokémon Trainer and receive your starter!"""
        user_id = str(ctx.author.id)

        if self._get_trainer(user_id):
            embed = discord.Embed(
                description="You're already registered! 😅\nUse `Mikasa team` to see your team!",
                color=0xFF0000,
            )
            await ctx.send(embed=embed)
            return

        self._register_trainer(user_id, ctx.author.display_name)
        starter_id = pd.pick_random_starter()
        starter = pd.KANTO_POKEMON[starter_id]
        self._add_pokemon(user_id, starter_id, level=5, slot=1)

        embed = discord.Embed(
            title="🎮  Welcome, Pokémon Trainer!",
            description=(
                f"Congratulations, {ctx.author.mention}! You're now a Pokémon Trainer! 🌟\n\n"
                f"Your first Pokémon is...\n\n"
                f"# {pd.TYPE_EMOJI.get(starter['types'][0], '❓')}  {starter['name']}!\n\n"
                f"**Types:** {pd.format_types(starter['types'])}\n"
                f"**Level:** 5\n"
                f"**HP:** {pd.calc_hp(starter['hp'], 5)}\n\n"
                f"🎒 **Starter Kit:**\n"
                f"<:pokeball:1479372175239544973> 5x Pokéballs  •  💊 3x Potions  •  💎 1x Revive\n\n"
                f"*Go catch 'em all, trainer!* ✨"
            ),
            color=TYPE_COLORS.get(starter["types"][0], MIKASA_COLOR),
        )
        embed.set_image(url=pd.get_sprite_url(starter_id))
        embed.set_footer(text="Mikasa Pokémon  •  Use 'Mikasa team' to see your team", icon_url=MIKASA_ICON)
        await ctx.send(embed=embed)

    @commands.command(name="team")
    async def show_team(self, ctx: commands.Context):
        """View your Pokémon team."""
        user_id = str(ctx.author.id)
        trainer = self._get_trainer(user_id)
        if not trainer:
            await ctx.send(embed=discord.Embed(
                description="You're not registered yet! Use `Mikasa pokestart` 🎮", color=0xFF0000))
            return

        team = self._get_team_pokemon(user_id)
        if not team:
            await ctx.send(embed=discord.Embed(
                description="You don't have any Pokémon! 😱", color=0xFF0000))
            return

        stored = self._get_stored_pokemon(user_id)

        embed = discord.Embed(
            title=f"🔴  {ctx.author.display_name}'s Team",
            color=MIKASA_COLOR,
        )

        for pp in team:
            info = pd.KANTO_POKEMON.get(pp["pokemon_id"], {})
            name = pp.get("nickname") or info.get("name", "???")
            types = pd.format_types(info.get("types", []))
            max_hp = pd.calc_hp(info.get("hp", 1), pp["level"])
            hp_bar = pd.render_hp_bar(pp["current_hp"], max_hp)
            status = "💀 FAINTED" if pp["is_fainted"] else ""

            moves_list = []
            for i in range(1, 5):
                mk = pp.get(f"move_{i}")
                if mk:
                    m = pd.MOVES.get(mk, {})
                    moves_list.append(f"`{m.get('name', mk)}`")
            moves_str = " • ".join(moves_list) if moves_list else "`None`"

            xp_needed = xp_to_next_level(pp["level"])
            embed.add_field(
                name=f"{'💀' if pp['is_fainted'] else '🔹'} Slot {pp['slot']}  •  {name}  •  Lv.{pp['level']}",
                value=(
                    f"{types}\n"
                    f"{hp_bar} {status}\n"
                    f"⭐ XP: {pp['xp']}/{xp_needed}\n"
                    f"⚔️ Moves: {moves_str}"
                ),
                inline=False,
            )

        embed.set_thumbnail(url=ctx.author.display_avatar.url)
        embed.add_field(
            name="🎒  Bag",
            value=(
                f"<:pokeball:1479372175239544973> Pokéballs: **{trainer['pokeballs']}**  •  "
                f"💊 Potions: **{trainer['potions']}**\n"
                f"💉 Super Potions: **{trainer.get('super_potions', 0)}**  •  "
                f"💎 Revives: **{trainer['revives']}**"
            ),
            inline=False,
        )
        if stored:
            embed.add_field(
                name=f"📦  PokéMachine ({len(stored)} stored)",
                value="Use `Mikasa pokemachine` to view stored Pokémon",
                inline=False,
            )
        embed.set_footer(text="Mikasa Pokémon", icon_url=MIKASA_ICON)
        await ctx.send(embed=embed)

    @commands.command(name="pokedex")
    async def pokedex(self, ctx: commands.Context, *, name: str = None):
        """Look up a Pokémon's stats. Usage: Mikasa pokedex pikachu"""
        if not name:
            await ctx.send(embed=discord.Embed(
                description="Please specify a Pokémon name! `Mikasa pokedex pikachu` 📖", color=0xFF0000))
            return

        # Find by name (case-insensitive)
        found = None
        for pid, pdata in pd.KANTO_POKEMON.items():
            if pdata["name"].lower() == name.lower():
                found = (pid, pdata)
                break

        if not found:
            await ctx.send(embed=discord.Embed(
                description=f"'{name}' not found! Check the spelling! 🤔", color=0xFF0000))
            return

        pid, pdata = found
        types = pd.format_types(pdata["types"])
        evo_text = "None"
        if pdata.get("evo"):
            evo_info = pd.KANTO_POKEMON.get(pdata["evo"][0], {})
            evo_text = f"{evo_info.get('name', '???')} at Lv.{pdata['evo'][1]}"

        embed = discord.Embed(
            title=f"📖  #{pid} — {pdata['name']}",
            color=TYPE_COLORS.get(pdata["types"][0], MIKASA_COLOR),
        )
        embed.add_field(name="Types", value=types, inline=True)
        embed.add_field(name="Evolution", value=evo_text, inline=True)
        embed.add_field(name="─── Base Stats ───", value="", inline=False)
        embed.add_field(name="❤️ HP", value=f"**{pdata['hp']}**", inline=True)
        embed.add_field(name="⚔️ ATK", value=f"**{pdata['atk']}**", inline=True)
        embed.add_field(name="🛡️ DEF", value=f"**{pdata['def']}**", inline=True)
        embed.add_field(name="💨 SPD", value=f"**{pdata['spd']}**", inline=True)
        embed.set_image(url=pd.get_sprite_url(pid))
        embed.set_footer(text="Mikasa Pokédex", icon_url=MIKASA_ICON)
        await ctx.send(embed=embed)

    @commands.command(name="pokemart")
    async def pokemart(self, ctx: commands.Context):
        """Open the Pokémon shop. Buy items with Mikasa Cash!"""
        user_id = str(ctx.author.id)
        trainer = self._get_trainer(user_id)
        if not trainer:
            await ctx.send(embed=discord.Embed(
                description="You're not registered yet! Use `Mikasa pokestart` 🎮", color=0xFF0000))
            return

        # Get balance
        bal_res = self.db.table("balances").select("money").eq("user_id", user_id).execute()
        balance = bal_res.data[0]["money"] if bal_res.data else 0

        embed = discord.Embed(
            title="🏪  PokéMart",
            description=(
                f"Welcome, **{ctx.author.display_name}**! What would you like to buy? 🛒\n\n"
                f"💰 **Mikasa Cash:** {balance:,}\n\n"
                f"**1️⃣  <:pokeball:1479372175239544973> Pokéball** — 500 cash\n"
                f"**2️⃣  💊 Potion** (heals 40% HP) — 300 cash\n"
                f"**3️⃣  💉 Super Potion** (heals to full HP) — 800 cash\n"
                f"**4️⃣  💎 Revive** (revives fainted Pokémon) — 1,000 cash\n\n"
                f"🎒 **Your Bag:** <:pokeball:1479372175239544973> {trainer['pokeballs']} | 💊 {trainer['potions']} | 💉 {trainer.get('super_potions', 0)} | 💎 {trainer['revives']}"
            ),
            color=GOLD_COLOR,
        )
        embed.set_footer(text="Mikasa PokéMart", icon_url=MIKASA_ICON)
        await ctx.send(embed=embed, view=ShopView(self, user_id))

    @commands.command(name="heal")
    async def heal_pokemon(self, ctx: commands.Context, slot: int = None):
        """Use a Revive on a fainted Pokémon. Usage: Mikasa heal [slot]"""
        user_id = str(ctx.author.id)
        trainer = self._get_trainer(user_id)
        if not trainer:
            await ctx.send(embed=discord.Embed(
                description="You're not registered yet! Use `Mikasa pokestart` 🎮", color=0xFF0000))
            return

        team = self._get_team_pokemon(user_id)
        fainted = [p for p in team if p.get("is_fainted")]
        if not fainted:
            await ctx.send(embed=discord.Embed(
                description="No fainted Pokémon! Your team is all healthy! 💪", color=0x2ECC71))
            return

        if trainer["revives"] <= 0:
            await ctx.send(embed=discord.Embed(
                description="You're out of Revives! Buy more at the PokéMart! 🏪", color=0xFF0000))
            return

        # If slot specified, revive that one
        if slot is not None:
            target = next((p for p in fainted if p["slot"] == slot), None)
            if not target:
                await ctx.send(embed=discord.Embed(
                    description=f"No fainted Pokémon in slot {slot}! 😅", color=0xFF0000))
                return
        elif len(fainted) == 1:
            target = fainted[0]
        else:
            # Multiple fainted — show selection
            desc = "Which Pokémon do you want to revive?\n\n"
            for p in fainted:
                info = pd.KANTO_POKEMON.get(p["pokemon_id"], {})
                name = p.get("nickname") or info.get("name", "???")
                desc += f"💀 **Slot {p['slot']}** — {name} (Lv.{p['level']})\n"
            desc += f"\nUse `Mikasa heal <slot>` to revive one!"
            await ctx.send(embed=discord.Embed(
                title="💎  Revive — Choose a Pokémon", description=desc, color=GOLD_COLOR))
            return

        info = pd.KANTO_POKEMON.get(target["pokemon_id"], {})
        max_hp = pd.calc_hp(info.get("hp", 1), target["level"])
        half_hp = max_hp // 2

        self.db.table("player_pokemon").update({
            "current_hp": half_hp,
            "is_fainted": False,
        }).eq("id", target["id"]).execute()
        self._update_trainer_items(user_id, revives=trainer["revives"] - 1)

        name = target.get("nickname") or info.get("name", "???")
        embed = discord.Embed(
            title="💎  Revived!",
            description=f"**{name}** has been revived with **{half_hp}/{max_hp}** HP! 🌟",
            color=0x2ECC71,
        )
        embed.set_thumbnail(url=pd.get_sprite_url(target["pokemon_id"]))
        embed.set_footer(text="Mikasa Pokémon", icon_url=MIKASA_ICON)
        await ctx.send(embed=embed)

    @commands.command(name="pokeheal")
    async def pokeheal(self, ctx: commands.Context, slot: int = None, potion_type: str = None):
        """Use a Potion on a Pokémon. Usage: Mikasa pokeheal [slot] [super]"""
        user_id = str(ctx.author.id)
        trainer = self._get_trainer(user_id)
        if not trainer:
            await ctx.send(embed=discord.Embed(
                description="You're not registered yet! Use `Mikasa pokestart` 🎮", color=0xFF0000))
            return

        use_super = potion_type and potion_type.lower() == "super"

        if use_super:
            if trainer.get("super_potions", 0) <= 0:
                await ctx.send(embed=discord.Embed(
                    description="You're out of Super Potions! Buy more at the PokéMart! 🏪", color=0xFF0000))
                return
        else:
            if trainer["potions"] <= 0:
                await ctx.send(embed=discord.Embed(
                    description="You're out of Potions! Buy more at the PokéMart! 🏪", color=0xFF0000))
                return

        team = self._get_team_pokemon(user_id)
        damaged = [p for p in team if not p["is_fainted"] and p["current_hp"] < pd.calc_hp(pd.KANTO_POKEMON.get(p["pokemon_id"], {}).get("hp", 1), p["level"])]

        if not damaged:
            await ctx.send(embed=discord.Embed(
                description="All your Pokémon are at full HP! 💪", color=0x2ECC71))
            return

        # If slot specified, heal that one
        if slot is not None:
            target = next((p for p in damaged if p["slot"] == slot), None)
            if not target:
                await ctx.send(embed=discord.Embed(
                    description=f"No damaged Pokémon in slot {slot} (or it's fainted)! 😅", color=0xFF0000))
                return
        elif len(damaged) == 1:
            target = damaged[0]
        else:
            # Multiple damaged — show selection
            desc = "Which Pokémon do you want to heal?\n\n"
            for p in damaged:
                info = pd.KANTO_POKEMON.get(p["pokemon_id"], {})
                name = p.get("nickname") or info.get("name", "???")
                max_hp = pd.calc_hp(info.get("hp", 1), p["level"])
                desc += f"🔹 **Slot {p['slot']}** — {name} (HP: {p['current_hp']}/{max_hp})\n"
            desc += f"\nUse `Mikasa pokeheal <slot>` or `Mikasa pokeheal <slot> super`!"
            await ctx.send(embed=discord.Embed(
                title="💊  Heal — Choose a Pokémon", description=desc, color=GOLD_COLOR))
            return

        info = pd.KANTO_POKEMON.get(target["pokemon_id"], {})
        max_hp = pd.calc_hp(info.get("hp", 1), target["level"])

        if use_super:
            new_hp = max_hp
            heal = max_hp - target["current_hp"]
            self._update_pokemon_hp(target["id"], new_hp)
            self._update_trainer_items(user_id, super_potions=trainer["super_potions"] - 1)
            title = "💉  Super Potion!"
        else:
            heal = int(max_hp * 0.4)
            new_hp = min(max_hp, target["current_hp"] + heal)
            self._update_pokemon_hp(target["id"], new_hp)
            self._update_trainer_items(user_id, potions=trainer["potions"] - 1)
            title = "💊  Healed!"

        name = target.get("nickname") or info.get("name", "???")
        embed = discord.Embed(
            title=title,
            description=(
                f"**{name}** recovered **+{heal} HP**!\n"
                f"{pd.render_hp_bar(new_hp, max_hp)}\n"
                f"`HP: {new_hp}/{max_hp}`"
            ),
            color=0x2ECC71,
        )
        embed.set_thumbnail(url=pd.get_sprite_url(target["pokemon_id"]))
        embed.set_footer(text="Mikasa Pokémon", icon_url=MIKASA_ICON)
        await ctx.send(embed=embed)

    # ── PokéMachine ────────────────────────────────────────────

    @commands.command(name="pokemachine")
    async def pokemachine(self, ctx: commands.Context):
        """View your stored Pokémon in the PokéMachine."""
        user_id = str(ctx.author.id)
        trainer = self._get_trainer(user_id)
        if not trainer:
            await ctx.send(embed=discord.Embed(
                description="You're not registered yet! Use `Mikasa pokestart` 🎮", color=0xFF0000))
            return

        stored = self._get_stored_pokemon(user_id)
        if not stored:
            await ctx.send(embed=discord.Embed(
                title="📦  PokéMachine",
                description="Your PokéMachine is empty! Catch more Pokémon! 🌿",
                color=MIKASA_COLOR))
            return

        embed = discord.Embed(
            title=f"📦  {ctx.author.display_name}'s PokéMachine",
            description=f"You have **{len(stored)}** Pokémon in storage.\nUse `Mikasa pokeswap <team_slot> <id>` to swap one onto your team!\n",
            color=MIKASA_COLOR,
        )

        for pp in stored[:10]:  # Show up to 10
            info = pd.KANTO_POKEMON.get(pp["pokemon_id"], {})
            name = pp.get("nickname") or info.get("name", "???")
            types = pd.format_types(info.get("types", []))
            max_hp = pd.calc_hp(info.get("hp", 1), pp["level"])
            hp_bar = pd.render_hp_bar(pp["current_hp"], max_hp)
            status = "💀 FAINTED" if pp["is_fainted"] else ""

            embed.add_field(
                name=f"{'💀' if pp['is_fainted'] else '🔹'} ID:{pp['id']}  •  {name}  •  Lv.{pp['level']}",
                value=f"{types}\n{hp_bar} {status}",
                inline=False,
            )

        if len(stored) > 10:
            embed.set_footer(text=f"Showing 10 of {len(stored)} stored Pokémon  •  Mikasa Pokémon", icon_url=MIKASA_ICON)
        else:
            embed.set_footer(text="Mikasa PokéMachine", icon_url=MIKASA_ICON)
        await ctx.send(embed=embed)

    @commands.command(name="pokeswap")
    async def pokeswap(self, ctx: commands.Context, team_slot: int = None, machine_id: int = None):
        """Swap a team Pokémon with one from PokéMachine. Usage: Mikasa pokeswap <slot> <id>"""
        user_id = str(ctx.author.id)
        trainer = self._get_trainer(user_id)
        if not trainer:
            await ctx.send(embed=discord.Embed(
                description="You're not registered yet! Use `Mikasa pokestart` 🎮", color=0xFF0000))
            return

        if team_slot is None or machine_id is None:
            await ctx.send(embed=discord.Embed(
                description="Usage: `Mikasa pokeswap <team_slot> <pokemachine_id>`\n\nUse `Mikasa team` and `Mikasa pokemachine` to see IDs! 📋",
                color=GOLD_COLOR))
            return

        if team_slot < 1 or team_slot > 5:
            await ctx.send(embed=discord.Embed(
                description="Team slot must be between 1 and 5! 🔢", color=0xFF0000))
            return

        # Check if user is in a battle
        if int(user_id) in self.active_battles or int(user_id) in self.active_pvp:
            await ctx.send(embed=discord.Embed(
                description="You can't swap Pokémon while in battle! ⚔️", color=0xFF0000))
            return

        # Get the team Pokémon at the given slot
        team = self._get_team_pokemon(user_id)
        team_poke = next((p for p in team if p["slot"] == team_slot), None)
        if not team_poke:
            await ctx.send(embed=discord.Embed(
                description=f"No Pokémon in team slot {team_slot}! 😅", color=0xFF0000))
            return

        # Get the stored Pokémon
        stored = self._get_stored_pokemon(user_id)
        machine_poke = next((p for p in stored if p["id"] == machine_id), None)
        if not machine_poke:
            await ctx.send(embed=discord.Embed(
                description=f"No Pokémon with ID {machine_id} in your PokéMachine! 😅", color=0xFF0000))
            return

        # Swap: team → slot 0, machine → team_slot
        self.db.table("player_pokemon").update({"slot": 0}).eq("id", team_poke["id"]).execute()
        self.db.table("player_pokemon").update({"slot": team_slot}).eq("id", machine_poke["id"]).execute()

        t_info = pd.KANTO_POKEMON.get(team_poke["pokemon_id"], {})
        m_info = pd.KANTO_POKEMON.get(machine_poke["pokemon_id"], {})
        t_name = team_poke.get("nickname") or t_info.get("name", "???")
        m_name = machine_poke.get("nickname") or m_info.get("name", "???")

        embed = discord.Embed(
            title="🔄  Pokémon Swapped!",
            description=(
                f"**{t_name}** → 📦 PokéMachine\n"
                f"**{m_name}** → 🔹 Team Slot {team_slot}\n\n"
                f"*Swap complete!* ✨"
            ),
            color=0x2ECC71,
        )
        embed.set_thumbnail(url=pd.get_sprite_url(machine_poke["pokemon_id"]))
        embed.set_footer(text="Mikasa Pokémon", icon_url=MIKASA_ICON)
        await ctx.send(embed=embed)

    # ── Secret Rare Candy (hidden) ────────────────────────────

    @commands.command(name="rarecandy", hidden=True)
    async def rarecandy(self, ctx: commands.Context, slot: int = 1, levels: int = 1):
        """🍬 Secret! Level up a Pokémon. Usage: Mikasa rarecandy <slot> [levels]"""
        user_id = str(ctx.author.id)
        trainer = self._get_trainer(user_id)
        if not trainer:
            await ctx.send(embed=discord.Embed(
                description="You're not registered yet! Use `Mikasa pokestart` 🎮", color=0xFF0000))
            return

        team = self._get_team_pokemon(user_id)
        target = next((p for p in team if p["slot"] == slot), None)
        if not target:
            await ctx.send(embed=discord.Embed(
                description=f"No Pokémon in slot {slot}! 😅", color=0xFF0000))
            return

        info = pd.KANTO_POKEMON.get(target["pokemon_id"], {})
        name = target.get("nickname") or info.get("name", "???")
        old_level = target["level"]
        new_level = min(100, old_level + levels)

        # Update moves at new level
        new_moves = pd.get_moves_at_level(target["pokemon_id"], new_level)
        move_data = {}
        for i, move in enumerate(new_moves[:4], 1):
            move_data[f"move_{i}"] = move

        # Calculate new max HP and set to full
        new_max_hp = pd.calc_hp(info.get("hp", 1), new_level)

        update = {
            "level": new_level,
            "xp": 0,
            "current_hp": new_max_hp,
            "is_fainted": False,
        }
        update.update(move_data)
        self.db.table("player_pokemon").update(update).eq("id", target["id"]).execute()

        # Check for evolution
        evo_msg = ""
        evo = info.get("evo")
        if evo and new_level >= evo[1]:
            evo_target = evo[0]
            evo_info = pd.KANTO_POKEMON.get(evo_target, {})
            self.db.table("player_pokemon").update({"pokemon_id": evo_target}).eq("id", target["id"]).execute()
            evo_msg = f"\n\n🌟 **{name}** evolved into **{evo_info.get('name', '???')}**! 🎊"
            name = evo_info.get("name", name)
            
        embed = discord.Embed(
            title="🍬  Rare Candy!",
            description=(
                f"**{name}** leveled up from **Lv.{old_level}** to **Lv.{new_level}**! 📈\n"
                f"HP fully restored to **{new_max_hp}**!"
                f"{evo_msg}"
            ),
            color=GOLD_COLOR,
        )
        embed.set_thumbnail(url=pd.get_sprite_url(evo_target if (evo and new_level >= evo[1]) else target["pokemon_id"]))
        embed.set_footer(text="🍬 Shhh... it's a secret!", icon_url=MIKASA_ICON)
        await ctx.send(embed=embed)

    # ── PvP Challenge ─────────────────────────────────────────

    @commands.command(name="pokechallenge")
    async def pokechallenge(self, ctx: commands.Context, opponent: discord.Member = None):
        """Challenge another trainer to a Pokémon battle! Usage: Mikasa pokechallenge @user"""
        if not opponent:
            await ctx.send(embed=discord.Embed(
                description="Mention a trainer to challenge! `Mikasa pokechallenge @user` ⚔️",
                color=0xFF0000))
            return

        challenger_id = str(ctx.author.id)
        opponent_id = str(opponent.id)

        # Validations
        if opponent.id == ctx.author.id:
            await ctx.send(embed=discord.Embed(
                description="You can't challenge yourself! 😅", color=0xFF0000))
            return
        if opponent.bot:
            await ctx.send(embed=discord.Embed(
                description="You can't challenge a bot! 🤖", color=0xFF0000))
            return

        c_trainer = self._get_trainer(challenger_id)
        if not c_trainer:
            await ctx.send(embed=discord.Embed(
                description="You're not registered yet! Use `Mikasa pokestart` 🎮",
                color=0xFF0000))
            return

        o_trainer = self._get_trainer(opponent_id)
        if not o_trainer:
            await ctx.send(embed=discord.Embed(
                description=f"{opponent.display_name} is not a registered trainer! 😢",
                color=0xFF0000))
            return

        if ctx.author.id in self.active_pvp or ctx.author.id in self.active_battles:
            await ctx.send(embed=discord.Embed(
                description="You're already in a battle! Finish it first! ⚔️",
                color=0xFF0000))
            return

        if opponent.id in self.active_pvp or opponent.id in self.active_battles:
            await ctx.send(embed=discord.Embed(
                description=f"{opponent.display_name} is already in a battle! ⚔️",
                color=0xFF0000))
            return

        c_lead = self._get_lead_pokemon(challenger_id)
        if not c_lead or c_lead.get("is_fainted"):
            await ctx.send(embed=discord.Embed(
                description="Your lead Pokémon is fainted! Heal it first! 💊",
                color=0xFF0000))
            return

        o_lead = self._get_lead_pokemon(opponent_id)
        if not o_lead or o_lead.get("is_fainted"):
            await ctx.send(embed=discord.Embed(
                description=f"{opponent.display_name}'s lead Pokémon is fainted! They need to heal first! 💊",
                color=0xFF0000))
            return

        c_info = pd.KANTO_POKEMON[c_lead["pokemon_id"]]
        o_info = pd.KANTO_POKEMON[o_lead["pokemon_id"]]

        embed = discord.Embed(
            title="⚔️  PvP Challenge!",
            description=(
                f"**{ctx.author.display_name}** challenges **{opponent.display_name}** to a Pokémon battle!\n\n"
                f"🔴 **{c_info['name']}** (Lv.{c_lead['level']}) {pd.format_types(c_info['types'])}\n"
                f"───── ⚡ VS ⚡ ─────\n"
                f"🔵 **{o_info['name']}** (Lv.{o_lead['level']}) {pd.format_types(o_info['types'])}\n\n"
                f"{opponent.mention}, do you accept?"
            ),
            color=GOLD_COLOR,
        )
        embed.set_footer(text="Mikasa Pokémon  •  60 seconds to respond", icon_url=MIKASA_ICON)

        view = PvPChallengeView(self, ctx.author, opponent, c_lead, o_lead)
        await ctx.send(embed=embed, view=view)

    # ── PvP Battle Embed Builder ──────────────────────────────

    def build_pvp_embed(self, s: PvPSession, p1_name: str, p2_name: str,
                        log: str = "", turn_user_id: int | None = None) -> discord.Embed:
        p1_poke = s.p1_pp.get("nickname") or s.p1_info["name"]
        p2_poke = s.p2_pp.get("nickname") or s.p2_info["name"]
        p1_types = pd.format_types(s.p1_info["types"])
        p2_types = pd.format_types(s.p2_info["types"])
        p1_bar = pd.render_hp_bar(s.p1_hp, s.p1_max_hp)
        p2_bar = pd.render_hp_bar(s.p2_hp, s.p2_max_hp)

        embed = discord.Embed(
            title="⚔️  PvP Battle Arena!",
            color=GOLD_COLOR,
        )

        turn_is_p2 = (turn_user_id == s.p2_id)
        
        # Determine the active player (whose turn it is)
        active_name = p2_name if turn_is_p2 else p1_name
        active_poke = p2_poke if turn_is_p2 else p1_poke
        active_pp = s.p2_pp if turn_is_p2 else s.p1_pp
        active_hp = s.p2_hp if turn_is_p2 else s.p1_hp
        active_max_hp = s.p2_max_hp if turn_is_p2 else s.p1_max_hp
        
        target_name = p1_name if turn_is_p2 else p2_name
        target_poke = p1_poke if turn_is_p2 else p2_poke
        target_pp = s.p1_pp if turn_is_p2 else s.p2_pp
        target_hp = s.p1_hp if turn_is_p2 else s.p2_hp
        target_max_hp = s.p1_max_hp if turn_is_p2 else s.p2_max_hp

        # Author icon: Active player
        embed.set_author(
            name=f"🎮 {active_name}'s Turn!  •  {active_poke}  [ HP: {active_hp}/{active_max_hp} ]",
            icon_url=pd.get_sprite_url(active_pp["pokemon_id"]),
        )

        # Thumbnail: Opponent
        embed.set_thumbnail(url=pd.get_sprite_url(target_pp["pokemon_id"]))

        # Field 1: P1
        embed.add_field(
            name=f"🔴 {p1_poke}  •  Lv.{s.p1_pp['level']}",
            value=f"**{p1_name}**\n{p1_types}\n{p1_bar}\n`HP: {s.p1_hp}/{s.p1_max_hp}`",
            inline=True,
        )

        # Field 2: VS
        embed.add_field(
            name="⚔️  VS  ⚔️",
            value=" \n \n ",  # Spacing
            inline=True,
        )

        # Field 3: P2
        embed.add_field(
            name=f"🔵 {p2_poke}  •  Lv.{s.p2_pp['level']}",
            value=f"**{p2_name}**\n{p2_types}\n{p2_bar}\n`HP: {s.p2_hp}/{s.p2_max_hp}`",
            inline=True,
        )

        if log:
            quoted_log = log.replace("\n", "\n> ")
            embed.add_field(name="📜 Battle Log", value=f"> {quoted_log}", inline=False)

        if turn_user_id:
            who = p1_name if turn_user_id == s.p1_id else p2_name
            embed.set_footer(text=f"{who}'s turn  •  Pick a move!", icon_url=MIKASA_ICON)
        else:
            embed.set_footer(text="Mikasa Pokémon PvP", icon_url=MIKASA_ICON)
        return embed

    # ── PvP Turn Execution ────────────────────────────────────

    async def execute_pvp_turn(self, interaction: discord.Interaction,
                               session: PvPSession, move_key: str):
        s = session
        # Determine attacker/defender
        if s.current_turn == s.p1_id:
            atk_pp, atk_info, atk_atk, atk_level = s.p1_pp, s.p1_info, s.p1_atk, s.p1_pp["level"]
            def_pp, def_info, def_def = s.p2_pp, s.p2_info, s.p2_def
            atk_label, def_label = "🔴", "🔵"
        else:
            atk_pp, atk_info, atk_atk, atk_level = s.p2_pp, s.p2_info, s.p2_atk, s.p2_pp["level"]
            def_pp, def_info, def_def = s.p1_pp, s.p1_info, s.p1_def
            atk_label, def_label = "🔵", "🔴"

        move = pd.MOVES.get(move_key, pd.MOVES["tackle"])
        eff = pd.get_type_effectiveness(move["type"], def_info["types"])
        stab = move["type"] in atk_info["types"]
        dmg = pd.calc_damage(atk_level, move["power"], atk_atk, def_def, eff, stab)

        # Apply damage
        if s.current_turn == s.p1_id:
            s.p2_hp = max(0, s.p2_hp - dmg)
        else:
            s.p1_hp = max(0, s.p1_hp - dmg)

        atk_name = atk_pp.get("nickname") or atk_info["name"]
        log = f"{atk_label} **{atk_name}** used **{move['name']}**! (-{dmg} HP)"
        if eff > 1.0:
            log += "\n🔥 *It's super effective!*"
        elif 0 < eff < 1.0:
            log += "\n😅 *Not very effective...*"
        elif eff == 0:
            log += "\n🚫 *It had no effect!*"
        if stab:
            log += " *(STAB)*"

        # Get display names
        p1_member = interaction.guild.get_member(s.p1_id)
        p2_member = interaction.guild.get_member(s.p2_id)
        p1_name = p1_member.display_name if p1_member else "Trainer 1"
        p2_name = p2_member.display_name if p2_member else "Trainer 2"

        # Check if defender fainted
        def_hp = s.p2_hp if s.current_turn == s.p1_id else s.p1_hp
        if def_hp <= 0:
            winner_id = s.current_turn
            loser_id = s.p2_id if winner_id == s.p1_id else s.p1_id
            winner_name = p1_name if winner_id == s.p1_id else p2_name
            loser_name = p2_name if winner_id == s.p1_id else p1_name
            winner_pp = s.p1_pp if winner_id == s.p1_id else s.p2_pp
            loser_pp = s.p2_pp if winner_id == s.p1_id else s.p1_pp
            winner_level = winner_pp["level"]
            loser_level = loser_pp["level"]

            # Update fainted status in DB
            self._update_pokemon_hp(loser_pp["id"], 0, fainted=True)

            # Grant XP (winner full, loser half)
            winner_xp = xp_from_battle(loser_level)
            loser_xp = xp_from_battle(loser_level) // 2

            self._grant_pvp_xp(winner_pp, winner_xp)
            self._grant_pvp_xp(loser_pp, loser_xp)
            
            # Check if loser has other living team members
            team_pokemon = self._get_team(str(loser_id))
            alive_team = [p for p in team_pokemon if p["id"] != loser_pp["id"] and not p["is_fainted"]]

            winner_poke = winner_pp.get("nickname") or pd.KANTO_POKEMON[winner_pp["pokemon_id"]]["name"]
            loser_poke = loser_pp.get("nickname") or pd.KANTO_POKEMON[loser_pp["pokemon_id"]]["name"]

            if alive_team:
                embed = discord.Embed(
                    title="💀  Pokémon Fainted!",
                    description=(
                        f"{log}\n\n"
                        f"💀 **{loser_name}**'s **{loser_poke}** fainted!\n"
                        f"Please choose another Pokémon to send out! 👇"
                    ),
                    color=0xE74C3C,
                )
                embed.set_thumbnail(url=pd.get_sprite_url(loser_pp["pokemon_id"]))
                embed.set_footer(text="Mikasa Pokémon PvP", icon_url=MIKASA_ICON)
                
                # Turn goes back to the person who needs to switch
                s.current_turn = loser_id
                
                await interaction.response.edit_message(embed=embed, view=SwitchView(self, None, s, loser_id))
                return
            else:
                s.is_over = True
                # Clean up tracking
                self.active_pvp.pop(s.p1_id, None)
                self.active_pvp.pop(s.p2_id, None)

                embed = discord.Embed(
                    title="🏆  PvP Battle Over!",
                    description=(
                        f"{log}\n\n"
                        f"💀 **{loser_name}**'s **{loser_poke}** fainted!\n"
                        f"{loser_name} is out of usable Pokémon!\n\n"
                        f"🎉 **{winner_name}** wins! 🎉\n\n"
                        f"⭐ {winner_name} earned **{winner_xp} XP**\n"
                        f"⭐ {loser_name} earned **{loser_xp} XP**\n\n"
                        f"*Both Pokémon have been fully healed!* 💚"
                    ),
                    color=0x2ECC71,
                )
                embed.set_thumbnail(url=pd.get_sprite_url(winner_pp["pokemon_id"]))
                embed.set_footer(text="Mikasa Pokémon PvP", icon_url=MIKASA_ICON)
                await interaction.response.edit_message(embed=embed, view=None)
                return

        # Switch turn
        s.current_turn = s.p2_id if s.current_turn == s.p1_id else s.p1_id
        embed = self.build_pvp_embed(s, p1_name, p2_name, log=log, turn_user_id=s.current_turn)
        await interaction.response.edit_message(
            embed=embed, view=PvPBattleView(self, s))

    def _grant_pvp_xp(self, pp: dict, gained_xp: int):
        """Grant XP to a Pokémon after PvP. Handles leveling/evolution."""
        new_xp = pp["xp"] + gained_xp
        new_level = pp["level"]
        while new_xp >= xp_to_next_level(new_level):
            new_xp -= xp_to_next_level(new_level)
            new_level += 1

        poke_id = pp["pokemon_id"]
        info = pd.KANTO_POKEMON[poke_id]

        # Check evolution
        evo = info.get("evo")
        if evo and new_level >= evo[1]:
            poke_id = evo[0]

        new_moves = pd.get_moves_at_level(poke_id, new_level)
        move_data = {
            "move_1": new_moves[0] if len(new_moves) > 0 else pp["move_1"],
            "move_2": new_moves[1] if len(new_moves) > 1 else pp.get("move_2"),
            "move_3": new_moves[2] if len(new_moves) > 2 else pp.get("move_3"),
            "move_4": new_moves[3] if len(new_moves) > 3 else pp.get("move_4"),
        }

        update = {"xp": new_xp, "level": new_level, "pokemon_id": poke_id}
        update.update(move_data)
        self.db.table("player_pokemon").update(update).eq("id", pp["id"]).execute()


# ══════════════════════════════════════════════════════════════
#  PVP CHALLENGE VIEW — Accept / Decline
# ══════════════════════════════════════════════════════════════
class PvPChallengeView(discord.ui.View):
    def __init__(self, cog: PokemonCog, challenger: discord.Member,
                 opponent: discord.Member, c_lead: dict, o_lead: dict):
        super().__init__(timeout=60)
        self.cog = cog
        self.challenger = challenger
        self.opponent = opponent
        self.c_lead = c_lead
        self.o_lead = o_lead
        self.responded = False

    @discord.ui.button(label="Accept", emoji="✅", style=discord.ButtonStyle.success)
    async def accept_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.opponent.id:
            await interaction.response.send_message(
                "Only the challenged player can accept! 😤", ephemeral=True)
            return
        if self.responded:
            return
        self.responded = True

        # Create PvP session (copy lead dicts so originals aren't mutated)
        import copy
        session = PvPSession(
            p1_id=self.challenger.id,
            p1_pokemon=copy.deepcopy(self.c_lead),
            p2_id=self.opponent.id,
            p2_pokemon=copy.deepcopy(self.o_lead),
        )

        self.cog.active_pvp[self.challenger.id] = session
        self.cog.active_pvp[self.opponent.id] = session

        # Decide who goes first by speed
        if session.p1_spd >= session.p2_spd:
            session.current_turn = session.p1_id
        else:
            session.current_turn = session.p2_id

        first_name = self.challenger.display_name if session.current_turn == session.p1_id else self.opponent.display_name

        embed = self.cog.build_pvp_embed(
            session,
            self.challenger.display_name,
            self.opponent.display_name,
            log=f"⚔️ Battle started! **{first_name}** goes first!",
            turn_user_id=session.current_turn,
        )
        await interaction.response.edit_message(embed=embed, view=PvPBattleView(self.cog, session))

    @discord.ui.button(label="Decline", emoji="❌", style=discord.ButtonStyle.danger)
    async def decline_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.opponent.id:
            await interaction.response.send_message(
                "Only the challenged player can decline! 😤", ephemeral=True)
            return
        if self.responded:
            return
        self.responded = True

        embed = discord.Embed(
            title="❌  Challenge Declined",
            description=f"**{self.opponent.display_name}** declined the challenge!",
            color=0xE74C3C,
        )
        embed.set_footer(text="Mikasa Pokémon PvP", icon_url=MIKASA_ICON)
        await interaction.response.edit_message(embed=embed, view=None)

    async def on_timeout(self):
        if not self.responded:
            self.responded = True
            embed = discord.Embed(
                title="⏰  Challenge Expired",
                description=f"**{self.opponent.display_name}** didn't respond in time!",
                color=0x95A5A6,
            )
            embed.set_footer(text="Mikasa Pokémon PvP", icon_url=MIKASA_ICON)
            if self.message:
                try:
                    await self.message.edit(embed=embed, view=None)
                except Exception:
                    pass


# ══════════════════════════════════════════════════════════════
#  PVP BATTLE VIEW — move buttons (no bag/run)
# ══════════════════════════════════════════════════════════════
class PvPBattleView(discord.ui.View):
    def __init__(self, cog: PokemonCog, session: PvPSession):
        super().__init__(timeout=30)
        self.cog = cog
        self.session = session
        self._build_buttons()

    def _build_buttons(self):
        self.clear_items()
        s = self.session
        # Show moves of the current turn's Pokémon
        if s.current_turn == s.p1_id:
            pp = s.p1_pp
        else:
            pp = s.p2_pp

        moves = [pp.get(f"move_{i}") for i in range(1, 5)]
        moves = [m for m in moves if m]

        for idx, mv_key in enumerate(moves):
            mv = pd.MOVES.get(mv_key, {})
            label = mv.get("name", mv_key)
            t = mv.get("type", "normal")
            emoji = pd.TYPE_EMOJI.get(t, "⚪")
            btn = discord.ui.Button(
                label=label, emoji=emoji,
                style=discord.ButtonStyle.primary,
                custom_id=f"pvp_move_{mv_key}_{s.current_turn}",
                row=idx // 2,
            )
            btn.callback = self._make_move_callback(mv_key)
            self.add_item(btn)

    def _make_move_callback(self, move_key: str):
        async def callback(interaction: discord.Interaction):
            if interaction.user.id != self.session.current_turn:
                await interaction.response.send_message(
                    "It's not your turn! ⏳", ephemeral=True)
                return
            if self.session.is_over:
                return
            await self.cog.execute_pvp_turn(interaction, self.session, move_key)
        return callback

    async def on_timeout(self):
        if self.session.is_over:
            return
        self.session.is_over = True
        # Forfeit — current turn player loses
        loser_id = self.session.current_turn
        winner_id = self.session.p2_id if loser_id == self.session.p1_id else self.session.p1_id

        self.cog.active_pvp.pop(self.session.p1_id, None)
        self.cog.active_pvp.pop(self.session.p2_id, None)

        embed = discord.Embed(
            title="⏰  Time's Up — Forfeit!",
            description=f"<@{loser_id}> took too long!\n\n🏆 <@{winner_id}> wins by forfeit!",
            color=0xE74C3C,
        )
        embed.set_footer(text="Mikasa Pokémon PvP", icon_url=MIKASA_ICON)
        if self.message:
            try:
                await self.message.edit(embed=embed, view=None)
            except Exception:
                pass


# ══════════════════════════════════════════════════════════════
#  SHOP VIEW
# ══════════════════════════════════════════════════════════════
class ShopView(discord.ui.View):
    def __init__(self, cog: PokemonCog, user_id: str):
        super().__init__(timeout=60)
        self.cog = cog
        self.user_id = user_id

    def _get_balance(self, user_id: str) -> int:
        res = self.cog.db.table("balances").select("money").eq("user_id", user_id).execute()
        return res.data[0]["money"] if res.data else 0

    def _deduct_balance(self, user_id: str, amount: int):
        current = self._get_balance(user_id)
        self.cog.db.table("balances").update({"money": current - amount}).eq("user_id", user_id).execute()

    @discord.ui.button(label="Pokéball (500💰)", emoji="<:pokeball:1479372175239544973>", style=discord.ButtonStyle.primary)
    async def buy_pokeball(self, interaction: discord.Interaction, button: discord.ui.Button):
        if str(interaction.user.id) != self.user_id:
            await interaction.response.send_message("This isn't your shop! 😤", ephemeral=True)
            return
        bal = self._get_balance(self.user_id)
        if bal < 500:
            await interaction.response.send_message("Not enough cash! 💸", ephemeral=True)
            return
        self._deduct_balance(self.user_id, 500)
        trainer = self.cog._get_trainer(self.user_id)
        self.cog._update_trainer_items(self.user_id, pokeballs=trainer["pokeballs"] + 1)
        await interaction.response.send_message(
            f"✅ 1x <:pokeball:1479372175239544973> Pokéball purchased! (Remaining: {trainer['pokeballs']+1})", ephemeral=True)

    @discord.ui.button(label="Potion (300💰)", emoji="💊", style=discord.ButtonStyle.success)
    async def buy_potion(self, interaction: discord.Interaction, button: discord.ui.Button):
        if str(interaction.user.id) != self.user_id:
            await interaction.response.send_message("This isn't your shop! 😤", ephemeral=True)
            return
        bal = self._get_balance(self.user_id)
        if bal < 300:
            await interaction.response.send_message("Not enough cash! 💸", ephemeral=True)
            return
        self._deduct_balance(self.user_id, 300)
        trainer = self.cog._get_trainer(self.user_id)
        self.cog._update_trainer_items(self.user_id, potions=trainer["potions"] + 1)
        await interaction.response.send_message(
            f"✅ 1x 💊 Potion purchased! (Remaining: {trainer['potions']+1})", ephemeral=True)

    @discord.ui.button(label="Super Potion (800💰)", emoji="💉", style=discord.ButtonStyle.success)
    async def buy_super_potion(self, interaction: discord.Interaction, button: discord.ui.Button):
        if str(interaction.user.id) != self.user_id:
            await interaction.response.send_message("This isn't your shop! 😤", ephemeral=True)
            return
        bal = self._get_balance(self.user_id)
        if bal < 800:
            await interaction.response.send_message("Not enough cash! 💸", ephemeral=True)
            return
        self._deduct_balance(self.user_id, 800)
        trainer = self.cog._get_trainer(self.user_id)
        self.cog._update_trainer_items(self.user_id, super_potions=trainer.get("super_potions", 0) + 1)
        await interaction.response.send_message(
            f"✅ 1x 💉 Super Potion purchased! (Remaining: {trainer.get('super_potions', 0)+1})", ephemeral=True)

    @discord.ui.button(label="Revive (1000💰)", emoji="💎", style=discord.ButtonStyle.secondary)
    async def buy_revive(self, interaction: discord.Interaction, button: discord.ui.Button):
        if str(interaction.user.id) != self.user_id:
            await interaction.response.send_message("This isn't your shop! 😤", ephemeral=True)
            return
        bal = self._get_balance(self.user_id)
        if bal < 1000:
            await interaction.response.send_message("Not enough cash! 💸", ephemeral=True)
            return
        self._deduct_balance(self.user_id, 1000)
        trainer = self.cog._get_trainer(self.user_id)
        self.cog._update_trainer_items(self.user_id, revives=trainer["revives"] + 1)
        await interaction.response.send_message(
            f"✅ 1x 💎 Revive purchased! (Remaining: {trainer['revives']+1})", ephemeral=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(PokemonCog(bot))
