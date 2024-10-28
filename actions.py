import requests

def action_response(action, user1, user2):
    """Fetch a GIF URL based on the action."""
    # Specify the endpoint based on the action
    url = f"https://api.otakugifs.xyz/gif?reaction={action}"

    # Fetch the GIFs from the specified URL
    try:
        response = requests.get(url)
        response.raise_for_status()  # Raise an error for bad responses
        gif = response.json().get('url')  # Assuming the response is a JSON object with a 'url' key
        
        if gif:
            return f"{user1} {action.capitalize()} {user2} action!", gif
            
    except Exception as e:
        print(f"Error fetching GIFs: {e}")

    return None, None  # Return None if something goes wrong
