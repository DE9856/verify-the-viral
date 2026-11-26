# Final-round presentation: 7 minutes

Two people: **Speaker** (talks, runs the slides) and **Driver** (laptop + Telegram on screen).
Deck: `submission/Check Before Share — Tech Stack.pptx`. Demo files: `~/Downloads/demo-day/`.
Skipped slides: 4, 5, 6, 8, 9, 12, 13 (show only if a judge asks).

## Before you go up (10 min earlier)
- [ ] Server running: `/health` shows `"ok":true` locally and via the ngrok URL.
- [ ] Send one throwaway clip to the bot (any clip, NOT the hero) and confirm it replies.
- [ ] Hero clip `2_HERO_spliced_notice.ogg` has never been checked on this DB (or else step 1 is an instant hit).
- [ ] Telegram Desktop open on the bot chat, zoomed in; hero file ready to drag in.
- [ ] Backup screen recording of the demo open in a second window.
- [ ] Deck in presenter mode, starting on slide 1.

## Run of show

| Time | Slide | Who | Say / do |
|---|---|---|---|
| 0:00 | 1 Cover | Speaker | "We're Check Before Share. Forward us a voice note and we tell you which seconds were made by AI, before you pass it on." |
| 0:15 | 2 Problem | Speaker | "The sneakiest fakes aren't fully fake. A real voice, the principal, the society secretary, with one sentence swapped in: *send ₹500 by tonight*. Ten seconds of audio is enough to clone a voice; we did it to ourselves on a gaming laptop. And forwarding is one tap; checking is impossible from inside a group chat." |
| 0:40 | 3 Who | Speaker | "It's for the parents and grandparents in family and college groups, the admins who add our bot once for the whole group, and anyone on a suspicious *it's me, I need money* call. In English, Hindi and Kannada." |
| 1:00 | **DEMO** | Driver | Switch to Telegram. |
| 1:00 | demo 1 | Driver drags in the hero clip | Speaker: "This is a real voice note of mine. One sentence in the middle is an AI clone of my voice. Exactly what lands in a family group." *(wait for the reply; keep talking: "It goes straight to DetectifAI's Aletheia…")* |
| 1:40 | demo 2 | Driver opens the card, plays the short voice reply (or taps **View timeline** → red stretch) | Speaker: "Partly AI, 10 to 14 seconds. Listen: that's the fake sentence. The card is made to be forwarded back into the group." |
| 2:20 | demo 3 | Driver forwards the same message to the bot again | Speaker: "Viral clips get forwarded thousands of times. Second time: instant, zero credits." |
| 2:40 | demo 4 | Driver points at 👍 / 👎 | Speaker: "Feedback goes back to DetectifAI. It also works from WhatsApp → Share, and live on a speakerphone call." |
| 3:00 | 7 Key finding | Speaker | "Why read the windows? On this exact clip Aletheia's headline said *real, 0.28*. Its 4-second windows said *fake, 0.98 to 1.00*. So we read every window: two overlapping fake windows make it *Partly AI*, one alone is *Unclear*. We check the voice, not the claim." |
| 3:45 | 10 Gates | Speaker | "Credits are the cost, so every clip passes five free gates first: the Telegram file id, the file hash, the decoded-audio hash, a Chromaprint fingerprint for WhatsApp and MP3 re-encodes, and sped-up or pitch-shifted copies. Only genuinely new audio reaches Aletheia. Memory is one SQLite file and a small fingerprint per clip." |
| 4:30 | 11 The diff | Speaker | "And if someone edits a clip we've seen, a fingerprint diff finds the changed stretch and we send only a 10-second excerpt. Four edited copies: 84 credits instead of 198, same answers." |
| 5:15 | 14 Results | Speaker | "We tested before we built. Real voices in three languages: zero false alarms out of 12. Clones: 6 out of 6 caught. Spliced notes: 6 out of 6, where the overall verdict missed 4. Different recordings: zero false cache hits in 612 pairs. Each result changed a design decision." |
| 6:00 | 15 Limits | Speaker | "What it can't do yet: our test set is small and male-only; a 1 to 2 second fake is often missed; calls need speakerphone; and a real person can still say something false. Every card says so." |
| 6:40 | 16 Stack / close | Speaker | "Python, FastAPI, ffmpeg, Chromaprint, and DetectifAI's REST, live and feedback APIs. **Check before you share.** Thank you." |
| 7:00 | | | Questions → `submission/check-before-share-explainer.pdf` (judging Q&A section). |

## If something goes wrong
- **Check takes more than 15 s:** Speaker keeps talking (problem, who it helps); don't stare at the screen.
- **Wi-Fi / Telegram down:** Driver switches to the backup recording; Speaker narrates the same lines.
- **Hero comes back instantly at demo 1:** say "we tested this one earlier, so it's already cached: that's our gate 1," and move on.
- **Running long at 5:15:** skip slide 14, say one line ("0 false alarms in 12 real notes, 6 of 6 fakes caught") and go to 15.

## Likely judge questions (short answers)
- *Does it flag real voices?* → 0 of 12 real notes. Offer to send `1_real_notice.ogg` live.
- *Why not just use Aletheia's verdict?* → It said real on our splice; the windows caught it (slide 7).
- *What does it cost?* → 2 credits/s, minimum 20; repeats free; edits ~21.
- *Can't someone dodge the cache by editing?* → A fuzzy match must pass the diff; a messy match gets a full re-check.
- *Phone calls?* → Speakerphone into live listen; apps can't capture call audio on Android/iOS.
