from flask import Flask, request, Response, redirect
import requests
from urllib.parse import quote
import re

app = Flask(__name__)


def get_youtube_path(id_type, identifier):
    paths = {
        "live": f"live/{identifier}",
        "handle": f"@{identifier}",
        "channel": f"channel/{identifier}",
        "customName": f"c/{identifier}",
        "user": f"user/{identifier}"
    }
    return paths.get(id_type, "")


def capitalize(string):
    return string.capitalize()


@app.route('/fetch.m3u8', methods=['GET'])
def fetch_m3u8():
    try:
        id_type = ''
        identifier = ''

        if 'live' in request.args:
            id_type = 'live'
            identifier = request.args.get('live')
        elif 'username' in request.args:
            id_type = 'handle'
            identifier = request.args.get('username')
        elif 'channel' in request.args:
            id_type = 'channel'
            identifier = request.args.get('channel')
        elif 'c' in request.args:
            id_type = 'customName'
            identifier = request.args.get('c')
        elif 'user' in request.args:
            id_type = 'user'
            identifier = request.args.get('user')
        else:
            return "No valid query parameter provided", 400

        if identifier:
            url = f"https://www.youtube.com/{get_youtube_path(id_type, identifier)}/live"
            response = requests.get(url)

            if response.status_code == 200:
                matches = re.search(r'(?<="hlsManifestUrl":").*\.m3u8', response.text)
                if matches:
                    hls_url = matches.group(0)
                    # Redirect to the restreaming endpoint
                    return redirect(f"/master.m3u8?uri={quote(hls_url)}", code=302)
                else:
                    return "HLS stream URL not found in the response", 500
            else:
                return f"YouTube URL ({url}) failed", 500
        else:
            return f"{capitalize(id_type)} ID not found in the query parameters", 400

    except Exception as e:
        return str(e), 500


@app.route('/master.m3u8')
def fetch_master_m3u8():
   
    m3u8_url = request.args.get('uri')
    if not m3u8_url:
        return "No .m3u8 URL provided", 400

    
    response = requests.get(m3u8_url)
    if response.status_code != 200:
        return "Error fetching master playlist", 500

    
    modified_playlist = []
    for line in response.text.splitlines():
        if line.startswith("https://"):
            # Encode the URL to handle special characters
            encoded_url = quote(line, safe='')
            modified_playlist.append(f"{request.host_url}variant?uri={encoded_url}")
        else:
            modified_playlist.append(line)

    return Response("\n".join(modified_playlist), content_type='application/vnd.apple.mpegurl')


@app.route('/variant')
def fetch_variant_m3u8():
    
    variant_url = request.args.get('uri')
    if not variant_url:
        return "Variant URL is required", 400

    
    response = requests.get(variant_url)
    if response.status_code != 200:
        return "Error fetching variant playlist", 500

    
    modified_playlist = []
    for line in response.text.splitlines():
        if line.startswith("https://"):
            # Encode the URL to handle special characters
            encoded_url = quote(line, safe='')
            modified_playlist.append(f"{request.host_url}segment?uri={encoded_url}")
        else:
            modified_playlist.append(line)

    return Response("\n".join(modified_playlist), content_type='application/vnd.apple.mpegurl')


@app.route('/segment')
def fetch_segment():
    
    segment_url = request.args.get('uri')
    if not segment_url:
        return "Segment URL is required", 400

    
    response = requests.get(segment_url, stream=True)
    if response.status_code != 200:
        return "Error fetching segment", 500

    # Stream the segment back to the client
    return Response(response.raw, content_type='video/MP2T')

if __name__ == "__main__":
    app.run()
