# Spotify Playlist Creator

Create a Spotify playlist from setlist data retrieved from Setlist.fm.

## Setup Instructions

1. **Install Python**:
   - Download and install Python from [python.org](https://www.python.org/downloads/).
   - Ensure you check the box to add Python to your PATH during installation.

2. **Clone the repository** or download the ZIP file and extract it.

3. **Create a Spotify Developer Account** at the [Spotify Developer Dashboard](https://developer.spotify.com/dashboard/) and log in.

4. **Create a new application** in the Spotify Developer Dashboard and copy the Client ID and Client Secret.
   - Set the Redirect URI to `http://localhost:5000/callback` in your Spotify application settings.

5. **Create a file named `.env` in the project folder** with the following content:
    ```
   REDIRECT_URI=http://localhost:5000/callback
   SPOTIFY_CLIENT_ID=your_spotify_client_id
   SPOTIFY_CLIENT_SECRET=your_spotify_client_secret
    ```

6. **Install the required packages**:
   - Open Powershell and navigate to the project folder.
   - Run the following command to install the required packages:
    ```
    pip install -r requirements.txt
    ```

7. **Run the application**:

    - Run the Python application directly.
    
    OR
    
    - Execute the following command in Powershell:
    ```
    python your_script.py
    ```
## Usage

1. **Authenticate with Spotify**: Follow the prompt to authenticate with Spotify.
2. **Search for Setlists**: Enter the name of the artist to retrieve setlist data from Setlist.fm.
3. **Create Playlist**: Select a setlist to create a Spotify playlist.

## Important Notes

- Make sure to set the Redirect URI in your Spotify application settings to the REDIRECT_URI in the .env file.

