# Recording Script — Voice Notes for the Accuracy Test

## Why we are recording these

We need to know if Aletheia (the deepfake detector) works on **real WhatsApp voice notes** in
**English, Hindi and Kannada**, before we build the product on it. So we record:

- **Real voices** → the detector should say "real". If it says "fake", that is a false alarm.
- **One AI clone of our own voice** → the detector should say "fake".
- **One mixed clip** (real voice + one fake sentence inside it) → the detector should point at the
  fake sentence only.

---

## How to record (same for every clip)

We record on the **phone's voice recorder app**, not inside WhatsApp.

1. Open the recorder app. If it has a quality setting, pick the normal or high setting.
2. Hold the phone the way you would for a voice note, about 15–20 cm from your mouth.
3. Read the script at a **normal speed**, like a normal voice note.
4. Small mistakes are fine. Do not restart for a small slip.
5. Each script takes about **30 seconds**.
6. Rename the file with the name shown below. Keep the phone's ending (`.m4a`, `.mp3`, ...).
7. Copy all the files to the laptop into `research/real-audio/` (this folder is not committed to git).

**Why it still counts as a WhatsApp test:** WhatsApp squeezes voice notes into a small, lower-quality
format (Opus). Claude Code will make a "WhatsApp-quality" copy of every recording with ffmpeg, and
we test **both**: the clean recording and the WhatsApp-quality copy. That also tells us if the
compression changes the result.

*Extra check, if you have 2 minutes:* also send recording No. 1 as a real WhatsApp voice note
(play it out loud and record it in WhatsApp, or just read Script A once more in WhatsApp). That
gives one real WhatsApp file to compare with our ffmpeg copy.

---

## The list of recordings (11 total)

| No. | File name | Who speaks | What to read |
|---|---|---|---|
| 1 | `real_en_person1` | Person 1 | Script A — English |
| 2 | `real_hi_person1` | Person 1 | Script A — Hindi |
| 3 | `real_kn_person1` | Person 1 | Script A — Kannada |
| 4 | `real_en_person2` | Person 2 | Script A — English |
| 5 | `real_hi_person2` | Person 2 | Script A — Hindi |
| 6 | `real_kn_person2` | Person 2 | Script A — Kannada |
| 7 | `notice_en` | Person 1 | Script B — English |
| 8 | `notice_hi` | Person 1 | Script B — Hindi |
| 9 | `notice_kn` | Person 1 | Script B — Kannada |
| 10 | `clone_en` | AI clone of Person 1 | Script B — English |
| 11 | `spliced_en` | Mix of No. 7 + the fake sentence | See "How to make the spliced clip" |

There are only two scripts:

- **Script A** is a normal chat message to a friend.
- **Script B** is a "please forward this" notice, the kind of message people fake.

Clone **only your own voice**, with permission. Never clone anyone else.

---
---

# SCRIPT A — Casual message to a friend

## Script A — English

Hi, it's me. Just reached college, the traffic near Silk Board was terrible again, almost forty minutes stuck.

Listen, the lab session got moved to Thursday afternoon, so we can't do the meeting then.

Can we meet tomorrow at the canteen around eleven instead?

Also, bring the charger I lent you last week, my phone is almost dead.

And tell Rahul the project file is in the group, he keeps asking me.

Okay, call me when you're free. Bye.

---

## Script A — Hindi (हिन्दी)

हाय, मैं बोल रहा हूँ। अभी कॉलेज पहुँचा, सिल्क बोर्ड के पास फिर से बहुत ट्रैफिक था, लगभग चालीस मिनट फँसा रहा।

सुनो, लैब वाला सेशन गुरुवार दोपहर को शिफ्ट हो गया है, तो उस दिन मीटिंग नहीं हो पाएगी।

क्या हम कल ग्यारह बजे कैंटीन में मिल सकते हैं?

और हाँ, पिछले हफ्ते जो चार्जर दिया था वो लेते आना, मेरा फ़ोन लगभग बंद होने वाला है।

राहुल को बोल देना कि प्रोजेक्ट फ़ाइल ग्रुप में है।

ठीक है, फ्री हो तो कॉल करना। बाय।

---

## Script A — Kannada (ಕನ್ನಡ)

ಹಾಯ್, ನಾನು ಮಾತಾಡ್ತಿದ್ದೀನಿ. ಈಗ ತಾನೇ ಕಾಲೇಜಿಗೆ ಬಂದೆ, ಸಿಲ್ಕ್ ಬೋರ್ಡ್ ಹತ್ರ ಮತ್ತೆ ತುಂಬಾ ಟ್ರಾಫಿಕ್ ಇತ್ತು, ಸುಮಾರು ನಲವತ್ತು ನಿಮಿಷ ಸಿಕ್ಕಾಕೊಂಡಿದ್ದೆ.

ಕೇಳು, ಲ್ಯಾಬ್ ಸೆಷನ್ ಗುರುವಾರ ಮಧ್ಯಾಹ್ನಕ್ಕೆ ಶಿಫ್ಟ್ ಆಗಿದೆ, ಅದಕ್ಕೆ ಆವತ್ತು ಮೀಟಿಂಗ್ ಆಗಲ್ಲ.

ನಾಳೆ ಹನ್ನೊಂದು ಗಂಟೆಗೆ ಕ್ಯಾಂಟೀನ್‌ನಲ್ಲಿ ಸಿಗೋಣ್ವಾ?

ಮತ್ತೆ, ಹೋದ ವಾರ ಕೊಟ್ಟಿದ್ದ ಚಾರ್ಜರ್ ತಗೊಂಡು ಬಾ, ನನ್ನ ಫೋನ್ ಸ್ವಿಚ್ ಆಫ್ ಆಗೋ ಹಾಗಿದೆ.

ರಾಹುಲ್‌ಗೆ ಪ್ರಾಜೆಕ್ಟ್ ಫೈಲ್ ಗ್ರೂಪ್‌ನಲ್ಲಿ ಇದೆ ಅಂತ ಹೇಳು.

ಸರಿ, ಫ್ರೀ ಇದ್ದಾಗ ಕಾಲ್ ಮಾಡು. ಬಾಯ್.

---
---

# SCRIPT B — "Please forward" notice

## Script B — English

Attention everyone in the apartment.

The water supply will be shut from tomorrow morning six a.m. till Saturday evening because of pipeline repair work.

Please store enough water tonight.

The association has also said the lift will be off from ten to two.

Forward this to everyone in your block, it's urgent. Thank you.

---

## Script B — Hindi (हिन्दी)

सभी अपार्टमेंट वालों के लिए ज़रूरी सूचना।

पाइपलाइन रिपेयर की वजह से कल सुबह छह बजे से शनिवार शाम तक पानी नहीं आएगा।

कृपया आज रात ही पानी भरकर रख लें।

एसोसिएशन ने बताया है कि लिफ्ट भी दस से दो बजे तक बंद रहेगी।

ये मैसेज अपने ब्लॉक में सबको फॉरवर्ड करें, बहुत ज़रूरी है। धन्यवाद।

---

## Script B — Kannada (ಕನ್ನಡ)

ಅಪಾರ್ಟ್‌ಮೆಂಟ್‌ನ ಎಲ್ಲರಿಗೂ ಮುಖ್ಯ ಸೂಚನೆ.

ಪೈಪ್‌ಲೈನ್ ರಿಪೇರಿ ಕೆಲಸದಿಂದ ನಾಳೆ ಬೆಳಿಗ್ಗೆ ಆರು ಗಂಟೆಯಿಂದ ಶನಿವಾರ ಸಂಜೆವರೆಗೆ ನೀರು ಬರಲ್ಲ.

ದಯವಿಟ್ಟು ಇವತ್ತು ರಾತ್ರಿನೇ ಸಾಕಷ್ಟು ನೀರು ತುಂಬಿಸಿಕೊಳ್ಳಿ.

ಲಿಫ್ಟ್ ಕೂಡ ಹತ್ತರಿಂದ ಎರಡು ಗಂಟೆವರೆಗೆ ಬಂದ್ ಇರುತ್ತೆ ಅಂತ ಅಸೋಸಿಯೇಷನ್ ಹೇಳಿದೆ.

ಈ ಮೆಸೇಜ್‌ನ ನಿಮ್ಮ ಬ್ಲಾಕ್‌ನ ಎಲ್ಲರಿಗೂ ಫಾರ್ವರ್ಡ್ ಮಾಡಿ, ತುಂಬಾ ಅರ್ಜೆಂಟ್. ಧನ್ಯವಾದಗಳು.

---
---

# How to make the spliced clip (No. 11)

This clip shows the dangerous case: a **real** voice note with **one fake sentence** hidden inside.

**Step 1.** Make the AI clone of Person 1's voice say this sentence (the fake sentence):

> The association also said everyone must send five hundred rupees to this number by tonight.

**Step 2.** Take recording No. 7 (`notice_en`, the real English notice).

**Step 3.** In an audio editor, paste the fake sentence **right after "Please store enough water
tonight."** That is about 10 seconds into the clip.

**Step 4.** Save it as `spliced_en`.

If it works, the detector should flag **only the seconds where the fake sentence is**, around 10 to
14 seconds.

*Optional: the same fake sentence in the other languages, if you have time and credits:*

- Hindi: एसोसिएशन ने कहा है कि सबको आज रात तक इस नंबर पर पाँच सौ रुपये भेजने हैं।
- Kannada: ಎಲ್ಲರೂ ಇವತ್ತು ರಾತ್ರಿ ಒಳಗೆ ಈ ನಂಬರ್‌ಗೆ ಐನೂರು ರೂಪಾಯಿ ಕಳಿಸಬೇಕು ಅಂತ ಅಸೋಸಿಯೇಷನ್ ಹೇಳಿದೆ.

---

# Before you record

- [ ] A native speaker has read the Hindi script and says it sounds natural.
- [ ] A native speaker has read the Kannada script and says it sounds natural.
- [ ] Both of you have agreed to be recorded.

# After you record

- Send all 11 files to Claude Code. It will run them through Aletheia and write the results into
  `research/real-world.md`.
- Cost: about 60 credits per clip, so about 650 credits in total.
