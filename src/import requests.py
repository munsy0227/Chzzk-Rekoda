import requests


def get_room_info(room_id):
    """Fetch room information from the Bilibili API."""
    url = "https://api.live.bilibili.com/room/v1/Room/get_info"
    params = {"room_id": room_id}
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
        "Referer": "https://www.bilibili.com/"}
    try:
        # Send the GET request with the parameter
        response = requests.get(url, params=params, headers=headers)
        response.raise_for_status()  # Raise an exception for HTTP errors

        info = response.json()
        if info['data']['live_status']:
            print("ofiasjhoifhsduofhwadofghsoghiosdfabnadfoghdfoahdfioghnrasdgi")
        print(info)
        # Parse the JSON response
        
    except requests.RequestException as e:
        print(f"Request failed: {e}")
        return None

if __name__ == "__main__":
    # Replace with the actual room ID
    room_id = '13318931'  # Example room ID
    room_info = get_room_info(room_id)
