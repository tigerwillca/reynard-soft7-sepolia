# reynard-soft7-sepolia

**Reynard Soft7 (SOFT7)** is live on **Robinhood Chain mainnet** (chain ID **4663**). Supply **7**.

The repository name stays `reynard-soft7-sepolia`.

| | |
| --- | --- |
| Landing | https://tigerwillca.github.io/reynard-soft7-sepolia/ |
| Contract | `0x73D7b2611509C14078e16f572bE5aC7D91879DC2` |
| Name / symbol / supply | Reynard Soft7 / SOFT7 / 7 |
| OpenSea | https://opensea.io/collection/reynard-soft7 |
| Token #1 | https://opensea.io/assets/robinhood/0x73D7b2611509C14078e16f572bE5aC7D91879DC2/1 |
| Blockscout | https://robinhoodchain.blockscout.com/address/0x73D7b2611509C14078e16f572bE5aC7D91879DC2 |
| X | https://x.com/tigerwillca |
| Mainnet announcement | https://x.com/tigerwillca/status/2103414595930968299 |
| Deployer | `0x86dF4D2fAA9aC25D408AA4E4Fb890B9918c5f066` |

`index.html` is the public landing. The hero is the Mask Depth banner `mask-depth-reynard/1.jpg` (853×1280), with a full-page forest loop (`soft7-bg-loop.webm` / `.mp4`, poster `soft7-bg-key-01.png`) and cards 1–7 at `#the-seven`. Card art is `images/033.jpg`–`images/039.jpg`. Token metadata is `meta/1.json`–`meta/7.json`. Collection metadata for the OpenSea editor is `meta/collection.json`.

The public site for this repository is [tigerwillca.github.io/reynard-soft7-sepolia](https://tigerwillca.github.io/reynard-soft7-sepolia/).

Built on Robinhood Chain · not a Robinhood product.

## GitHub Pages

`.github/workflows/pages.yml` publishes an allowlisted public directory on every push to `main`. `scripts/assemble_public_site.sh` builds that directory from the landing page, token metadata, card art, and hero media. The workflow asks GitHub to enable Pages on the first run (`enablement: true`) and deploy with **GitHub Actions**.

Creating the site from Actions fails with `Resource not accessible by integration` (`enablement: true` cannot call the Pages API for this repository). Turn Pages on once: **Settings → Pages → Build and deployment → Source: GitHub Actions**. Do not choose the `/docs` folder, and do not deploy the repository root. A root deploy would publish agent config and scripts along with the site.

Token `external_url`, collection `external_link`, and the landing canonical URL use:

https://tigerwillca.github.io/reynard-soft7-sepolia/

Leave the Pages folder off `/docs`. That path only sends people to the project landing. A `.nojekyll` file is included in the published directory so Pages serves the files as-is.

## OpenSea metadata

`tokenURI(1)`–`tokenURI(7)` on `0x73D7b2611509C14078e16f572bE5aC7D91879DC2` are pinned to commit `3a049e2` (`meta/1.json`–`meta/7.json` on jsDelivr). The contract has `setBaseURI(string)` and no `setTokenURI`. After these metadata files are on `main`, the owner points `setBaseURI` at `https://cdn.jsdelivr.net/gh/tigerwillca/reynard-soft7-sepolia@<that-commit>/meta/` and refreshes the seven tokens on OpenSea. Image URLs stay on commit `ae7d304`.

`meta/collection.json` is the collection record for the OpenSea editor (logo, banner, site, 750 bps to the royalty router). The contract has no `contractURI()`.

`mask-depth-reynard/1.jpg` is the 853×1280 Mask Depth banner (commit `cad54c6`). `mask-depth-reynard/1.json` and `reynard-prime/meta/0.json` both use that pinned image. The full locked PNG is not in this repository. Those two JSON files still describe different tokens (Mask Depth versus Reynard Prime).

## Earlier soft gate

The Sepolia contract `0xa96141BFB1dfeffeDcf5E07F204CFC70B2f1AF3f` was the prior soft gate. The live drop is the Robinhood Chain mainnet contract above.
