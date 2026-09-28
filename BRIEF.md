# Reynard Soft7 — one source of truth

This file is the brief. The pieces below are folded in. Art proofs are in `proofs/`. The 777 contract is in `contracts/Soft7MascotCards.sol`. Nothing in the proof set has been minted.

Go-live was 10:00. That clock drifted. The target is still tonight, and tonight's ship is this approval set. Mint stays closed until these proofs are approved.

## What the cards are

Reynard Soft7 mascot cards on Robinhood Chain, chain ID 4663. Supply 777. Waves are 7, then 77 a week: the opening week can mint 7, and each week after that adds 77, stopping at 777.

Description, used as written on every proof:

> reynard-soft7 mascot cards on robinhood chain. ten percent of every mint routes back to soft7 holders proportional to what they hold. stake your card, feed the treasury, pull when you're ready.

Socials: [discord.gg/tigerwillca](https://discord.gg/tigerwillca), [x.com/tigerwillca](https://x.com/tigerwillca), [tigerwillca.github.io](https://tigerwillca.github.io/).

Traits, five and no others: `tier`, `color`, `eyes`, `signature`, `globe`.

## Paint, eyes, amulet, clothing

Art is paintbrush, with bristle and canvas. It is not flat digital art.

Every character comes off the mascot. Face paint is on all of them. No two characters share a signature. The seven signatures, from the base mask to the most complex, are Brow Line, Cheek Marks, Solar Tick, Heart Band, Throat Outline, Layered Contour, Crown Glyphs.

The eyes are the identity. They stay fixed. That is non-negotiable. Fox cards keep Amber Lock. They do not pick up a new eye color when the mask blooms. These proofs were drawn as separate paintings, so the amber eyes match by identity and not yet by pixels. Pixel-locking from one approved master happens before any mint. Do not regenerate the set to chase that lock unless this file is read first and the approver asks for a new pass.

The potion is the engine. Color arrives in this order, slowly: the amulet catches the chakra color first, then the mask paint blooms, then the belt buckle. On a still proof, the tier shows how far that bloom has gone. The amulet shifts with the chakra color. It is the quietest layer. You only notice it when you look for it, and it is what ties the card together.

Clothing and the belt are incorporated. They are silent details, not loud ones.

Tigers are thin and lean, with no fat, in a Star Wars Jedi or wizard pose, on the stark side, with no extra colors. The first tier 3 proof read as bulky. It was redrawn once after that read. The file in `proofs/art/03.png` is the lean pass: narrow waist, Pale Lock eyes, one gold brow tick, gold only as the faint amulet. Do not draw the tiger again unless the approver asks.

Foxes are the pristine mascot, on the colorful side, full body visible, nothing cropped. All characters are centered, eyes locked on the viewer, feet on solid ground, in a dynamic Star Wars figure stance.

Colors differ on every tier and follow the potion and the chakras: Crimson, Amber, Gold, Green, Blue, Indigo, Violet.

The banner is a purple-lime backdrop, Reynard as the hero, and the seventh-gate potion orb. The wide banner proof still clips the fox at the shins. That was read after two passes. Do not generate another banner unless the approver asks. The seven card PNGs are the token media.

## Media

One image per token. PNG or GIF. Not the JPEG test versions in `images/033.jpg`–`images/039.jpg`. The generator returned JPEG bytes under `.png` names; those files were re-encoded so the bytes are real PNGs (`89 50 4E 47`). A wallet that sniffs the file sees a PNG.

## Money

Ten percent of every mint routes back to Soft7 holders proportional to what they hold. The holder stakes the card, which feeds their weight in the treasury, and pulls when they are ready. The card stays in the wallet while it is staked.

The Robinhood wallet ending in 77a is `0xe53bdb2118585d5B2cD06a117d3A036AFA70677a`. It receives the other ninety percent of each mint. If nobody is staked when a mint happens, the ten percent is paid there too, because there is no holder weight to pull against.

Royalty is 7.5% (750 bps), paid to that same wallet on secondary sales.

Compile the proof contract with solc 0.8.24, optimizer on, 200 runs, EVM `cancun`, metadata bytecode hash, viaIR off. The standard JSON for a Blockscout blue check is `contracts/compiler-input.json` after `scripts/compile_proof.sh`.

The proof contract starts with proofs unapproved and waves closed. `approveProofs()` then `openWaves()` are owner calls for after this set is accepted. They have not been sent. No deploy. No mint.

## Why the live tokens do not show in wallets

Live contract `0x73D7b2611509C14078e16f572bE5aC7D91879DC2` on chain 4663. Read from the chain on 28 Sep 2026:

- `tokenURI(1)` through `tokenURI(7)` point at commit `3a049e2` on jsDelivr. Those JSON files point at `images/033.jpg`–`images/039.jpg` on commit `ae7d304`. The responses are `image/jpeg`. They are the test versions.
- Blockscout has `media_type: null` and `thumbnails: null` on all seven. The indexer stored the JPEG URL and did not produce media a wallet can render.
- The constructor base URI was the older Sepolia commit `de98736`. Blockscout still describes tokens 4–7 as Sepolia testnet cards. Tokens 1–3 were refetched later. Wallets that cached the first fetch are holding the testnet text and the JPEGs.
- `is_verified` is false. There is no blue check. Compiler metadata in the bytecode is solc 0.8.24, IPFS `QmXzj3Udp5RXzPES8xuX11CUpZKauk4bkw2hkCdcvLpkRj`. The gateways did not return that metadata. The error selectors in the bytecode are not a full current OpenZeppelin ERC-721, so a guessed source would not verify. Do not retry verification by uploading a lookalike. The blue check needs the compiler JSON that matches that CID, submitted to Blockscout.
- `MAX_SUPPLY()` is 7. The 777 waves cannot be minted on this contract. Royalty on it is already 750 bps to `0x64c00a1c2d354F66aD5660548098F7cA25CEeb38`.

The display fix, after approval, is one step: point this contract's `setBaseURI` at a directory of JSON whose `image` is one PNG or GIF each, served as `application/json` and `image/png` or `image/gif`. jsDelivr does that. `raw.githubusercontent.com` serves JSON as `text/plain`, which wallets drop. `scripts/encode_set_base_uri.py` prints the calldata and does not send it. Then refetch the seven token instances on Blockscout so the stale Sepolia cache is replaced.

## What not to retry

Read this file before another art pass or another verification attempt. The failed paths already walked:

- Blind IPFS fetches of the compiler CID (429, timeout, payment required).
- Guessing an OpenZeppelin body for the live bytecode. The missing `ERC721InvalidSender` selector means it will not match.
- Calling the JPEG tests the wallet images. They are why the media type is empty.
- Minting, deploying, or calling `setBaseURI` before these proofs are approved.
