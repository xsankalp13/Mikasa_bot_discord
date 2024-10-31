import requests
import os
import random

TENOR_API_KEY = os.getenv("TENOR_API_KEY")

# def action_response(action, user1, user2):
#     """Fetch a GIF URL based on the action."""
#     # Specify the endpoint based on the action
#     url = f"https://api.otakugifs.xyz/gif?reaction={action}"

#     # Fetch the GIFs from the specified URL
#     try:
#         response = requests.get(url)
#         response.raise_for_status()  # Raise an error for bad responses
#         gif = response.json().get('url')  # Assuming the response is a JSON object with a 'url' key
        
#         if gif:
#             return f"{user1} {action.capitalize()} {user2} action!", gif
            
#     except Exception as e:
#         print(f"Error fetching GIFs: {e}")

#     return None, None  # Return None if something goes wrong









def get_gif_url(query):
    """Fetches a GIF URL from Tenor API based on the action query."""
    random_number = random.randint(0, 50)
    url = f"https://g.tenor.com/v1/search?q=anime-{query}-cute&key={TENOR_API_KEY}&pos={random_number}&limit=1&media_filter=minimal"
    response = requests.get(url)
    if response.status_code == 200:
        data = response.json()
        return data["results"][0]["media"][0]["gif"]["url"]
    return None

def action_response(action, user1, user2):
    """Constructs the action response with a GIF URL and a message."""
    gif_url = get_gif_url(action)
    message = f"{user1} {action}ed {user2}!"
    return message, gif_url