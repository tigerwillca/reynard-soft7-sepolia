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

`index.html` is the public landing: Mask Depth Reynard hero (`soft7-mascot-hero.png`), a full-page forest loop (`soft7-bg-loop.webm` / `.mp4`, poster `soft7-bg-key-01.png`), and the Seventh Gate link orb. Card art is `images/033.jpg`–`images/039.jpg`. Token metadata is `meta/1.json`–`meta/7.json`.

Built on Robinhood Chain · not a Robinhood product.

## GitHub Pages

`.github/workflows/pages.yml` publishes the repository root (`/`) on every push to `main`. The workflow asks GitHub to enable Pages on the first run (`enablement: true`) and deploy with **GitHub Actions**.

If that run cannot create the site, turn Pages on once: **Settings → Pages → Build and deployment → Source: GitHub Actions**. Do not choose the `/docs` folder.

After a successful deploy, the site is:

https://tigerwillca.github.io/reynard-soft7-sepolia/

Leave the Pages folder off `/docs`. That path only sends people to the root landing.

If you would rather publish without Actions, set **Source** to **Deploy from a branch**, branch **`main`**, folder **`/ (root)`**, and do that instead of GitHub Actions. The workflow above is the setup this repo expects. A `.nojekyll` file is at the repo root so a branch deploy serves the files as-is.

## Earlier soft gate

The Sepolia contract `0xa96141BFB1dfeffeDcf5E07F204CFC70B2f1AF3f` was the prior soft gate. The live drop is the Robinhood Chain mainnet contract above.
