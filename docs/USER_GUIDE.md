# OpenParty v1.0 — User Guide

Welcome to OpenParty! This guide explains how to set up OpenParty, host a watch party, or join one.

## 1. Initial Setup (Everyone must do this once)
OpenParty relies on standard tools like VLC and Syncplay. To ensure you have exactly what you need without messing up your computer, we've provided a simple setup script.

1. Download the OpenParty folder.
2. Inside, open the `setup` folder.
3. Right-click `setup.cmd` and select **Run as Administrator**.
4. The script downloads and verifies VLC, Syncplay, aria2c, and the Microsoft Visual C++ runtime required by Syncplay. It installs the runtime tools, registers `.oparty` files for your Windows user, and writes progress to `%ProgramData%\OpenParty\install.log`. Python and qBittorrent are not needed to run the packaged `OpenParty.exe`.

## 2. Hosting a Watch Party

As the host, your job is to create the party file and send it to your friends.

1. Run `OpenParty.exe` (or `python app/main.py` if running from source).
2. Click **Create Party**.
3. Fill in the details:
   - **Party Name:** What you're watching (e.g., "Friday Movie Night").
   - **Room Name:** A unique name for your Syncplay room (e.g., "daves-movie-room").
   - **Password:** Optional, but recommended to keep strangers out.
   - **Media Source:** Click **Browse Video File...** and pick your video file. OpenParty creates a torrent, verifies it, starts seeding with aria2c, and fills in the magnet link. (Or, you can paste an existing magnet link.)
   - **Optional Fields:** You can add a description, file size, or name hint (if you use the Create Torrent button, size and name hint are filled automatically).
4. Wait for OpenParty to verify the file against the torrent. It starts the built-in seeder and confirms the exact torrent is active before enabling **Start Watch Party**.
5. Export the party file and send it to your friends (for example, in Discord).
6. Keep OpenParty running while guests download. The host screen shows connected peers, their estimated completion, and current transfer rates. Use **Stop Sharing** to stop serving the file while playback continues.

OpenParty opens a narrow Windows Firewall rule for aria2 on TCP/UDP ports 51413-51420 during setup. A home router can still block incoming connections: forward TCP and UDP ports 51413-51420 to the host PC. If the ISP uses carrier-grade NAT (CGNAT), direct peer hosting may not work; use a mesh VPN or a public relay.

## 3. Joining a Watch Party

As a guest, joining is incredibly simple.

1. When your friend sends you a `.oparty` file, double-click it. (Or open `OpenParty.exe`, click **Join Party**, and select the file).
2. Review the party details on the screen to ensure it's the right movie.
3. Click **Start Party**.
4. OpenParty will handle everything else automatically:
   - It will fetch the metadata and download the movie into your `Downloads/OpenParty` folder.
   - Once complete, it will verify the file size and integrity.
   - It will keep the verified torrent available to other peers while OpenParty stays open.
   - Finally, it will launch Syncplay and VLC, automatically pointing them at the movie and connecting you to the host's room.
   - The playback screen shows live connections and per-peer transfer rates. Peer progress is estimated from the pieces that peer reports; BitTorrent does not provide party member names or an invite-wide attendance list.

## 4. Troubleshooting

OpenParty is designed to fix itself or give you clear instructions if something goes wrong. If you encounter an error, read the message on screen—it will tell you exactly what to do.

- **"Syncplay is missing"**: Run `setup/setup.cmd` again as Administrator.
- **"Disk Full"**: Free up space on your `C:\` drive. OpenParty will resume where it left off when you click Try Again.
- **"Download Stalled" / no peers**: Ask the host to keep OpenParty open and check the upload status. For remote guests, forward TCP/UDP 51413-51420 to the host PC. A router port forward cannot bypass CGNAT or a network that blocks peer-to-peer traffic.

If you ever need to ask a technical friend for help, click **View Logs** on the main menu and send them the `launcher.log` and `syncplay.log` files.
