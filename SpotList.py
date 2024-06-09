import requests
from bs4 import BeautifulSoup
import tkinter as tk
from tkinter import messagebox, scrolledtext
import threading
import time
from dotenv import load_dotenv
import os
import webbrowser
import urllib.parse
from http.server import BaseHTTPRequestHandler, HTTPServer
import datetime

# Load environment variables from .env file
load_dotenv()

SPOTIFY_CLIENT_ID = "SPOTIFY_CLIENT_ID"
SPOTIFY_CLIENT_SECRET = os.getenv('SPOTIFY_CLIENT_SECRET')
REDIRECT_URI = 'http://localhost:5000/callback'

if not SPOTIFY_CLIENT_ID:
    raise Exception("SPOTIFY_CLIENT_ID not found in environment variables. Make sure to set it in the .env file.")

if not SPOTIFY_CLIENT_SECRET:
    raise Exception("SPOTIFY_CLIENT_SECRET not found in environment variables. Make sure to set it in the .env file.")

auth_code = None
access_token = None
user_profile = None
details = None
playlist_id = None

class OAuthCallbackHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        global auth_code
        path = self.path
        if path.startswith('/callback'):
            query = urllib.parse.urlparse(path).query
            params = urllib.parse.parse_qs(query)
            auth_code = params.get('code')[0]
            self.send_response(200)
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            self.wfile.write(b"Authorization code received! You can close this window.")
            threading.Thread(target=self.server.shutdown).start()

    def log_message(self, format, *args):
        return

def run_server():
    global httpd
    server_address = ('127.0.0.1', 5000)
    httpd = HTTPServer(server_address, OAuthCallbackHandler)
    try:
        httpd.serve_forever()
    except Exception as e:
        print(f"Error while running server: {e}")
    finally:
        httpd.server_close()

def shutdown_server():
    global httpd
    if httpd:
        httpd.shutdown()
        httpd = None

httpd = None
server_thread = None

def get_authorization_url():
    client_id = SPOTIFY_CLIENT_ID
    redirect_uri = REDIRECT_URI
    scopes = 'user-read-private user-read-email playlist-modify-private playlist-modify-public'
    prompt = 'consent'

    auth_url = 'https://accounts.spotify.com/authorize'
    auth_params = {
        'client_id': client_id,
        'response_type': 'code',
        'redirect_uri': redirect_uri,
        'scope': scopes,
        'prompt': prompt
    }
    auth_request_url = f"{auth_url}?{urllib.parse.urlencode(auth_params)}"
    return auth_request_url

def open_authorization_url():
    auth_url = get_authorization_url()
    webbrowser.open(auth_url)

def get_access_token(auth_code):
    url = "https://accounts.spotify.com/api/token"
    headers = {
        "Content-Type": "application/x-www-form-urlencoded"
    }
    data = {
        "grant_type": "authorization_code",
        "code": auth_code,
        "redirect_uri": REDIRECT_URI,
        "client_id": SPOTIFY_CLIENT_ID,
        "client_secret": SPOTIFY_CLIENT_SECRET
    }
    try:
        response = requests.post(url, headers=headers, data=data)
        response.raise_for_status()
        response_data = response.json()
        return response_data['access_token']
    except requests.exceptions.RequestException as e:
        print(f"Request failed: {e}")
        return None

def get_user_profile(access_token):
    url = "https://api.spotify.com/v1/me"
    headers = {
        'Authorization': f'Bearer {access_token}'
    }
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Request failed: {e}")
        return None

def authorize_user():
    global auth_code, access_token, user_profile, server_thread
    if server_thread is None or not server_thread.is_alive():
        server_thread = threading.Thread(target=run_server)
        server_thread.start()
    
    open_authorization_url()

    while auth_code is None:
        time.sleep(1)

    access_token = get_access_token(auth_code)
    
    if access_token:
        user_profile = get_user_profile(access_token)
    
    if user_profile:
        playlist_amount = playlist_count(access_token)
        user_name = user_profile.get('display_name', 'User').split(' ')[0]
        user_followers = user_profile.get('followers', {}).get('total', 'Unknown')
        label_user_name.config(text=f"Hello, {user_name}!\n{user_followers} followers\n{playlist_amount} playlists", fg="green")
        auth_button.pack_forget()
        add_playlist.config(state=tk.DISABLED, text="Nothing Selected")
    else:
        label_user_name.config(text="Hello, User. Please authenticate", fg="red")

def playlist_count(access_token):
    url = 'https://api.spotify.com/v1/me/playlists'
    headers = {
        'Authorization': f'Bearer {access_token}'
    }
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        return response.json()['total']
    else:
        print(f"Failed to retrieve playlists: {response.status_code}")
    return 0

def API_create_playlist(API_output):
    global access_token, user_profile, details, playlist_id, playlist_name
    
    try:
        if not details:
            raise ValueError("Could not find the details.")
        
        tour_name = details["Tour Name"]
        tour_text = f"-{tour_name}-" if tour_name else "-"
        playlist_name = f'{details["Artist Name"]}{tour_text}{details["Venue"]}'
        playlist_description = f'{details["Artist Name"]}{tour_text}{details["Venue"]}-{details["Date"]}---Created {datetime.datetime.now().date()}'

        user_id = user_profile['id']
        url = f"https://api.spotify.com/v1/users/{user_id}/playlists"
        headers = {
            'Authorization': f'Bearer {access_token}',
            'Content-Type': 'application/json'
        }
        data = {
            'name': playlist_name,
            'description': playlist_description,
            'public': False
        }

        API_output.insert(tk.END, f'\nCreating Playlist...\n    "{playlist_name}"\n')
        response = requests.post(url, headers=headers, json=data)
        response.raise_for_status()
        playlist = response.json()
        playlist_id = playlist['id']
        API_output.insert(tk.END, f"Playlist '{playlist_name}' created successfully!\n")

        API_add_songs(API_output, playlist_name, playlist_id, details['Songs'])

    except ValueError as e:
        API_output.insert(tk.END, f'Error: {e}\n')
        messagebox.showerror("Error", str(e))
    except Exception as e:
        API_output.insert(tk.END, f'An unexpected error occurred: {e}\n')
        messagebox.showerror("Unexpected Error", str(e))

def get_song(song_name, artist_name):
    global access_token
    headers = {
        'Authorization': f'Bearer {access_token}'
    }
    query = f'track:{song_name} artist:{artist_name}'
    url = f'https://api.spotify.com/v1/search?q={urllib.parse.quote(query)}&type=track&limit=1'

    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        search_results = response.json()
        if search_results['tracks']['items']:
            first_track = search_results['tracks']['items'][0]
            track_id = first_track['id']
            print(f'Track ID: {track_id}')
            return track_id
        else:
            print('No tracks found for this query.')
            return None
    else:
        print(f'Error: {response.status_code}')
        print(response.json())
        return None



def API_add_songs(API_output, playlist_name, playlist_id, songs):
    global access_token
    try:
        success_num=0
        failed_num=0
        failed_songs=[]
        url = f"https://api.spotify.com/v1/playlists/{playlist_id}/tracks"
        headers = {
            'Authorization': f'Bearer {access_token}',
            'Content-Type': 'application/json'
        }
        
        uris = []
        for song in songs:
            track_id = get_song(song['name'], song['artist'])
            API_output.insert(tk.END, f"Adding '{song['name']}'...\n")
            if track_id:
                uris.append(f'spotify:track:{track_id}')
                success_num+=1
            else:
                API_output.insert(tk.END, f"Failed to add '{song['name']}'!!\n")
                failed_num+=1
                failed_songs.append({song['name']})
        
        if not uris:
            API_output.insert(tk.END, f'No valid songs found to add to playlist "{playlist_name}".\n')
            return

        data = {
            'uris': uris
        }

        API_output.insert(tk.END, f'\nAdding {len(uris)} songs to playlist "{playlist_name}"\n')
        response = requests.post(url, headers=headers, json=data)
        response.raise_for_status()
        API_output.insert(tk.END, f"{success_num} songs added to playlist '{playlist_name}' successfully!\n")
        if failed_num >0:
            API_output.insert(tk.END, f"{failed_num} songs failed to resolve track_uri.\n")
            API_output.insert(tk.END, f"Failed songs:\n")
            for x in failed_songs:
                API_output.insert(tk.END, f"{x}\n")

    except Exception as e:
        API_output.insert(tk.END, f'An unexpected error occurred while adding songs: {e}\n')
        messagebox.showerror("Unexpected Error", str(e))

def on_search():
    artist_name = entry_artist_name.get()
    if not artist_name:
        messagebox.showwarning("Input Error", "Please enter an Artist Name")
        return
    
    url = f'https://www.setlist.fm/search?query={artist_name.replace(" ", "+")}'
    setlists = scrape_setlist_data(url)
    
    listbox_setlists.delete(0, tk.END)
    global setlist_urls
    setlist_urls = []
    if setlists:
        for setlist in setlists:
            formatted_text = f"{setlist['Artist Name']}--{setlist['Date']}-{'-' + setlist['Tour Name'] if setlist['Tour Name'] else ''}-{setlist['Venue']}"
            listbox_setlists.insert(tk.END, formatted_text)
            setlist_urls.append(setlist['URL'])
    else:
        messagebox.showinfo("No Results", "No setlists found")

def on_select(event):
    global details
    widget = event.widget
    selection = widget.curselection()
    if selection:
        index = selection[0]
        url = setlist_urls[index]
        details = scrape_setlist_details(url)
        if details.get('Songs'):
            add_playlist.config(state=tk.NORMAL, text="Create Playlist", command=but_cr_playlist, fg="green")
        else:
            add_playlist.config(text="No songs in set list", state=tk.DISABLED)
        if not user_profile:
            add_playlist.config(text="Not Authenticated", state=tk.DISABLED)
        
        if details:
            setlist_details.delete(1.0, tk.END)
            setlist_details.insert(tk.END, f"Artist: {details['Artist Name']}\n")
            if details['Tour Name'] is not None:
                setlist_details.insert(tk.END, f"Tour: {details['Tour Name']}\n")
            setlist_details.insert(tk.END, f"Venue: {details['Venue']}\n")
            setlist_details.insert(tk.END, f"{details['Date']}\n")
            if not details['Songs']:
                setlist_details.insert(tk.END, "\nNo songs listed.")
            else:
                setlist_details.insert(tk.END, "Songs:\n")
                for song in details['Songs']:
                    setlist_details.insert(tk.END, f"    - {song['name']}\n")
    else:
        add_playlist.config(state=tk.DISABLED, text="Nothing Selected")



def scrape_setlist_data(url):
    try:
        response = requests.get(url)
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        messagebox.showerror("Error", f"Failed to retrieve the webpage. Status code: {response.status_code}")
        return []
    
    soup = BeautifulSoup(response.content, 'html.parser')
    setlist_divs = soup.find_all('div', class_='col-xs-12 setlistPreview')
    
    setlists = []
    for div in setlist_divs:
        date_div = div.find('div', class_='condensed dateBlock')
        set_url = div.find('h2')
        details_div = div.find('div', 'details')
        artist_name = tour_name = venue_name = None

        for span in details_div.find_all('span'):
            if "Artist:" in span.text:
                artist_name = span.find('a').find('span').get_text()
            elif "Tour:" in span.text:
                tour_name = span.find('a').get_text()
            elif "Venue:" in span.text:
                venue_name = span.find('a').find('span').get_text()
                
        month = date_div.find('span', 'month').text
        day = date_div.find('span', 'day').text
        year = date_div.find('span', 'year').text
        date = f"{month} {day}, {year}"
        setlist_url = 'https://www.setlist.fm/' + set_url.find('a')['href']
        
        setlists.append({
            'Artist Name': artist_name,
            'Tour Name': tour_name,
            'Date': date,
            'Venue': venue_name,
            'URL': setlist_url
        })
    
    return setlists

def scrape_setlist_details(url):
    try:
        response = requests.get(url)
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        messagebox.showerror("Error", f"Failed to retrieve the setlist. Status code: {response.status_code}")
        return None
    
    soup = BeautifulSoup(response.content, 'html.parser')
    headline = soup.find('div', 'setlistHeadline')
    if not headline:
        messagebox.showerror("Error", "Failed to parse the setlist page.")
        return None

    artist_name = headline.find('a').get_text()
    details_div = soup.find('div', {'class': 'infoContainer'})
    try:
        tour_name = details_div.find('p').find('a').get_text()
    except AttributeError:
        tour_name = None
    venue = headline.find_all('a')[1].get_text()
    date_block = soup.find('div', 'dateBlock')
    date = f"{date_block.find('span', 'month').text} {date_block.find('span', 'day').text}, {date_block.find('span', 'year').text}"
    songs = [{'name': song.text, 'artist': artist_name} for song in soup.find_all('a', 'songLabel')]
    
    return {
        'Artist Name': artist_name,
        'Tour Name': tour_name,
        'Venue': venue,
        'Date': date,
        'Songs': songs
    }



def but_cr_playlist():
    API_window = tk.Tk()
    API_window.title("Spotify API Output")
    
    API_output = scrolledtext.ScrolledText(API_window, width=60, height=25)
    API_output.pack(pady=5)

    thread = threading.Thread(target=API_create_playlist, args=(API_output,))
    thread.daemon = True
    thread.start()

    API_window.mainloop()

def on_closing():
    global server_thread
    try:
        if server_thread and server_thread.is_alive():
            shutdown_server()
            server_thread.join()
            server_thread = None
    except Exception as e:
        print(f"Error shutting down server: {e}")
    root.destroy()

root = tk.Tk()
root.title("Setlist Scraper")

label_user_name = tk.Label(root, text="Hello, User. Please authenticate", fg="red")
label_user_name.pack(pady=5)

auth_button = tk.Button(root, text="Authenticate", command=authorize_user)
auth_button.pack(pady=5)

label_artist_name = tk.Label(root, text="Enter Artist Name:")
label_artist_name.pack(pady=5)

entry_artist_name = tk.Entry(root, width=30)
entry_artist_name.pack(pady=5)

button_search = tk.Button(root, text="Search", command=on_search)
button_search.pack(pady=5)

add_playlist = tk.Button(root, text="Nothing Selected", command=but_cr_playlist, state=tk.DISABLED)
add_playlist.pack(pady=5)

listbox_setlists = tk.Listbox(root, width=80, height=15)
listbox_setlists.pack(pady=5)
listbox_setlists.bind('<<ListboxSelect>>', on_select)

setlist_details = scrolledtext.ScrolledText(root, width=60, height=25)
setlist_details.pack(pady=5)

root.protocol("WM_DELETE_WINDOW", on_closing)

root.mainloop()
