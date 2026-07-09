# OpenParty v1.0 — User Guide

Welcome to OpenParty! This guide explains how to set up OpenParty, host a watch party, or join one.

## 1. Initial Setup (Everyone must do this once)
OpenParty relies on standard tools like VLC and Syncplay. To ensure you have exactly what you need without messing up your computer, we've provided a simple setup script.

1. Download the OpenParty folder.
2. Inside, open the `setup` folder.
3. Right-click `setup.cmd` and select **Run as Administrator**.
4. The script will securely install VLC, Syncplay, and aria2 (the download engine) using Windows Package Manager (`winget`). It will also register `.oparty` files so you can double-click them to join.

## 2. Hosting a Watch Party

As the host, your job is to create the party file and send it to your friends.

1. Run `OpenParty.exe` (or `python app/main.py` if running from source).
2. Click **Create Party**.
3. Fill in the details:
   - **Party Name:** What you're watching (e.g., "Friday Movie Night").
   - **Room Name:** A unique name for your Syncplay room (e.g., "daves-movie-room").
   - **Password:** Optional, but recommended to keep strangers out.
   - **Media Source:** A magnet link for the movie.
   - **Optional Fields:** You can add a description, file size, or name hint (to help OpenParty select the right file if the magnet contains multiple videos).
4. Click **Export Party File**.
5. Send the resulting `.oparty` file to your friends (e.g., drag and drop it into Discord).

## 3. Joining a Watch Party

As a guest, joining is incredibly simple.

1. When your friend sends you a `.oparty` file, double-click it. (Or open `OpenParty.exe`, click **Join Party**, and select the file).
2. Review the party details on the screen to ensure it's the right movie.
3. Click **Start Party**.
4. OpenParty will handle everything else automatically:
   - It will fetch the metadata.
   - It will download the movie into your `Downloads/OpenParty` folder.
   - Once complete, it will verify the file size and integrity.
   - Finally, it will launch Syncplay and VLC, automatically pointing them at the movie and connecting you to the host's room.

## 4. Troubleshooting

OpenParty is designed to fix itself or give you clear instructions if something goes wrong. If you encounter an error, read the message on screen—it will tell you exactly what to do.

- **"Syncplay is missing"**: Run `setup/setup.cmd` again as Administrator.
- **"Disk Full"**: Free up space on your `C:\` drive. OpenParty will resume where it left off when you click Try Again.
- **"Download Stalled"**: The torrent might be dead. Ask the host to check the magnet link.

If you ever need to ask a technical friend for help, click **View Logs** on the main menu and send them the `launcher.log` and `syncplay.log` files.
