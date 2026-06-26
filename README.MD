# # Knowledge Vault

Knowledge Vault is a self-hosted landing page for offline knowledge. It starts Kiwix, Calibre-Web, MeiliSearch, and Jellyfin from a single script, then gives you one search box to find content across wikis, books, and local files. No internet required.

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
