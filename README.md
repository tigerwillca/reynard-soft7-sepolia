# reynard-soft7-sepolia

**Reynard Soft7 (SOFT7)** is live on **Robinhood Chain mainnet** (chain ID **4663**). Supply **7**.

The repository name stays `reynard-soft7-sepolia`.

| | |
| --- | --- |
| Landing (live) | https://tigerwillca.github.io/ |
| Project Pages | https://tigerwillca.github.io/reynard-soft7-sepolia/ (404 until Pages is created in Settings) |
| Contract | `0x73D7b2611509C14078e16f572bE5aC7D91879DC2` |
| Name / symbol / supply | Reynard Soft7 / SOFT7 / 7 |
| OpenSea | https://opensea.io/collection/reynard-soft7 |
| Token #1 | https://opensea.io/assets/robinhood/0x73D7b2611509C14078e16f572bE5aC7D91879DC2/1 |
| Blockscout | https://robinhoodchain.blockscout.com/address/0x73D7b2611509C14078e16f572bE5aC7D91879DC2 |
| X | https://x.com/tigerwillca |
| Mainnet announcement | https://x.com/tigerwillca/status/2103414595930968299 |
| Deployer | `0x86dF4D2fAA9aC25D408AA4E4Fb890B9918c5f066` |

`index.html` is the public landing: Mask Depth Reynard hero (`soft7-mascot-hero.png`), a full-page forest loop (`soft7-bg-loop.webm` / `.mp4`, poster `soft7-bg-key-01.png`), and cards 1–7 at `#the-seven`. Card art is `images/033.jpg`–`images/039.jpg`. Token metadata is `meta/1.json`–`meta/7.json`. Collection metadata for the OpenSea editor is `meta/collection.json`.

The live site today is [tigerwillca.github.io](https://tigerwillca.github.io/) (the user Pages repo). This repo’s project Pages site is not created yet.

Built on Robinhood Chain · not a Robinhood product.

## GitHub Pages

`.github/workflows/pages.yml` publishes the repository root (`/`) on every push to `main`. The workflow asks GitHub to enable Pages on the first run (`enablement: true`) and deploy with **GitHub Actions**.

Creating the site from Actions fails with `Resource not accessible by integration` (`enablement: true` cannot call the Pages API for this repository). Turn Pages on once: **Settings → Pages → Build and deployment → Source: GitHub Actions**. Do not choose the `/docs` folder. Until that exists, OpenSea `external_url` and the canonical link use `https://tigerwillca.github.io/`, which already serves the landing.

After a successful deploy, the site is:

https://tigerwillca.github.io/reynard-soft7-sepolia/

Leave the Pages folder off `/docs`. That path only sends people to the root landing.

If you would rather publish without Actions, set **Source** to **Deploy from a branch**, branch **`main`**, folder **`/ (root)`**, and do that instead of GitHub Actions. The workflow above is the setup this repo expects. A `.nojekyll` file is at the repo root so a branch deploy serves the files as-is.

## OpenSea metadata

`tokenURI(1)`–`tokenURI(7)` on `0x73D7b2611509C14078e16f572bE5aC7D91879DC2` are pinned to commit `3a049e2` (`meta/1.json`–`meta/7.json` on jsDelivr). The contract has `setBaseURI(string)` and no `setTokenURI`. After these metadata files are on `main`, the owner points `setBaseURI` at `https://cdn.jsdelivr.net/gh/tigerwillca/reynard-soft7-sepolia@<that-commit>/meta/` and refreshes the seven tokens on OpenSea. Image URLs stay on commit `ae7d304`.

`meta/collection.json` is the collection record for the OpenSea editor (logo, banner, site, 750 bps to the royalty router). The contract has no `contractURI()`.

Mask Depth / Reynard Prime (`mask-depth-reynard/1.jpg`) is still the placeholder string `PLACEHOLDER_WILL_REPLACE`. The locked PNG named in `mask-depth-reynard/README.md` is not in this repository, so that 1/1 is not ready to list.

## Earlier soft gate

The Sepolia contract `0xa96141BFB1dfeffeDcf5E07F204CFC70B2f1AF3f` was the prior soft gate. The live drop is the Robinhood Chain mainnet contract above.
