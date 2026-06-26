# Knowledge Vault

Knowledge Vault is a self-hosted landing page for offline knowledge. It starts Kiwix, Calibre-Web, MeiliSearch, and Jellyfin from a single script, then gives you one search box to find content across wikis, books, and local files. No internet required.

![](readme-gif.gif)


## Services
| Service      | Port | Purpose                         |
| ------------ | ---- | ------------------------------- |
| Landing page | 5500 | Search UI                       |
| Kiwix        | 8888 | Offline ZIM wikis               |
| Calibre-Web  | 8083 | Book library (read/search PDFs) |
| MeiliSearch  | 7700 | Full-text search index          |
| Jellyfin     | 8096 | Media server                    |

## Data
You must prepare your own drive and add your own data. This repo expects a directory with the following structure:

/root  
├── media  
├── pdf  
└── zim

- Add ZIM files to the `zim` folder. You can find some [here](https://browse.library.kiwix.org/).
- Add pdf files to the `pdf` folder.
- Add media to the media folder. More info on Jellyfin setup later.

## Hardware
You can run the servers and store the data on the same machine, but if you require more space, use a separate drive for the data. If you choose, you can make the data portable. Use a portable hard drive or a multi-drive enclosure like [this](https://www.newegg.com/wavlink-rapidfire-h4-k35284a-4-bay-ssd-enclosure-for-2-5-3-5-inch-sata-drive/p/0VN-0069-00056?item=9SIA6PFKK50098) for more storage space. In this configuration, each system you plug the drive into should have the source code installed.

# Installation
1. Create and activate a python virtual environment with python 3.12.
```bash
python -m venv venv
source venv/bin/activate
```
2. Install packages.
```bash
pip install -r requirements.txt
```
3. Download Meilisearch [executable](https://github.com/meilisearch/meilisearch/releases) for your OS and add to root directory.
4. Install Jellyfin according to their [documentation](https://jellyfin.org/docs/general/installation/).

# Setup
1. Add data - download some ZIMs and PDFs (Ignore Jellyfin for now), and add to your vault drive according to the directory structure in the data section.
2. Run search ingestion. Depending on the size of your vault, this can take anywhere from a few seconds to several days.
```bash
python ingest.py --path /path/to/vault
```
3. Jellyfin -
	1. [Install](https://jellyfin.org/docs/general/installation/) according to your OS.
	2. Complete the [Setup Wizard](https://jellyfin.org/docs/general/post-install/setup-wizard).
	3. Create folders in your /media directory for Movies, Shows, Music, or whatever else you'd like to add. Add your media to these folders. More info [here](https://jellyfin.org/docs/general/server/libraries).
	4. Give jellyfin access to the folders - `sudo chmod o+rx /mnt /mnt/vault /mnt/vault/media`
	5. Go to your [server instance](http://127.0.0.1:8096/) in a browser and [add the libraries](https://jellyfin.org/docs/general/server/libraries).

# Start

From the root directory, run `./start.sh`. To expose to your local network, add the `--expose` flag.