import requests
import utils


print(utils.actions)

url = "https://api.otakugifs.xyz/gif?reaction=kiss"


response = requests.get(url)
print(response)
response.raise_for_status()  # Raise an error for bad responses
gif = response.json().get('url')  # Assuming the response is a JSON object with a 'gifs' key
print(" GIF URL: ", gif)