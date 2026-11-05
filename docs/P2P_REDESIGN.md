# P2P hosting and transfer redesign

## Phase 1: Correct torrent lifecycle — implemented

- Creating a party hashes the selected file into a BitTorrent v1 torrent.
- The managed aria2 seeder loads that torrent, verifies the file's pieces, and reports ready only when its active info hash matches the invite and the full file is complete.
- Joining always goes through aria2, including when a matching file is already in the download folder. This validates the actual torrent and lets the completed copy seed instead of returning the host's source path as a fake download.
- aria2 remains alive after a guest finishes downloading, seeds with no ratio cap, and stops when OpenParty closes or another download replaces it.

## Phase 2: Connectivity and transfer visibility — implemented

- Host and guest aria2 processes use TCP and UDP ports 51413-51420 for BitTorrent and DHT.
- Setup creates narrowly scoped Windows Firewall rules for only the managed aria2 executable and that port range.
- Host and playback screens show connected peers, an estimated peer completion percentage from the BitTorrent bitfield, upload/download rates, and bytes sent where aria2 reports them.
- Peer rows use temporary labels. BitTorrent does not expose a party member's name, and the app cannot count invited or offline guests that are not connected to this device.
- “Seeder active” reports local process state; it does not claim that a remote network can reach the host.

## Phase 3: Internet reachability beyond direct peers — infrastructure required

The local firewall rule does not configure the user's router. For direct remote hosting, forward TCP and UDP 51413-51420 to the host PC. Some routers and ISPs use CGNAT or block inbound traffic, where manual forwarding cannot help. Supporting those networks reliably requires a public relay or hosted transport service, or users can connect through a mesh VPN. OpenParty does not currently operate such a service.
