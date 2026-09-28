# Soft7 brief

Reynard Soft7 on Robinhood Chain (chain ID 4663). Supply 7. Contract `0x73D7b2611509C14078e16f572bE5aC7D91879DC2`.

Staking is built in this repository. No Anvil. No third-party staking protocol.

## Stake

Every NFT stakes inside the project. Tokens 1–7 are the stake. There is no separate lockup contract to hand a card to.

A card earns from the treasury slice. On a secondary sale the creator fee is 7.5%. The royalty router sends 80% of that fee to the creator and keeps the rest, including dust, for the treasury. When the fee divides evenly, the treasury slice is 1.5% of the sale price. The treasury is the giveback vault `0x6B0E22d322c967DFBDB57D027cE53D1D32F7711A`.

The longer you hold, the more it earns. A card's weight is the number of seconds it has been held. A funding of the treasury slice is split by those weights. A card that just arrived has weight 0, so its portion stays in the treasury until time has passed. Wei that does not divide evenly stays in the treasury.

Sell it and the mask cracks. That is the cost of leaving. Unpaid rewards on that card return to the treasury, the hold resets, and the mask is cracked. While it is cracked, weight is the hold scaled by how far the card is through a 90-day heal. A cracked card held for half a quarter earns half of what a whole mask earns for the same time. A full quarter of continuous holding heals the mask. Selling again cracks it again.

`scripts/soft7_stake.py` is the book. It does not start a chain and it does not call another protocol.

The live vault still pays holders on-chain, quarterly, from the slice that reaches it. The book above is how this project weighs that slice.

## One treasury

Pulse feeds Project X. Project X feeds Soft7. Soft7 feeds Pulse.

Three projects, one treasury, all tied together. Each leg is recorded, and the wei is booked once, into the same vault. The loop does not keep a second or third pot.

## Landing

The public page is `index.html`, on a dark background (`#07050f`).

The top banner is not a still. Mask Depth Reynard stands in front, and motion plays behind him: the forest loop (`soft7-bg-loop.webm` / `.mp4`) with the phoenix loop (`phoenix-banner.gif`) screened across the lower half.

Under the banner the page shows the seven cards, a Mint button (primary supply is already 7; the button opens the OpenSea collection), the staking rules, and the dividend: 1.5% of each secondary sale, paid quarterly on-chain.

The metadata server on port 8000 serves that page from the repository root as soon as the files are on disk. GitHub Pages for this repository publishes the same root after the site exists and this branch is on `main`.
