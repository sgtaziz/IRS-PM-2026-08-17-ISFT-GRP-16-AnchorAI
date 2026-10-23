# Video

Two five minute videos for the module brief. Video files are not committed. Only the scripts, the slide decks and this note are.

| Promotion | System design |
|---|---|
| [![Promotion video](https://img.youtube.com/vi/opfahkYKg6U/maxresdefault.jpg)](https://youtu.be/opfahkYKg6U) | [![System design video](https://img.youtube.com/vi/t8pL02oRPBU/maxresdefault.jpg)](https://youtu.be/t8pL02oRPBU) |

| Video | Script | Brief | Final file name |
|---|---|---|---|
| Promotion | `script-promo.md` | Business pain and value, use case demo, pricing | `IRS-PM-2026-08-17-ISFT-GRP-16-AnchorAI-promotion.mp4` |
| System design | `script-technical.md` | High level system design, technical explanation of the use cases | `IRS-PM-2026-08-17-ISFT-GRP-16-AnchorAI-system.mp4` |

## Structure

Each video has three sections of about 1:40, and each member speaks about his own work. The first speaker opens with a short team and product intro, and the last closes with an outro.

| Section | Speaker | Area | Promotion | System design |
|---|---|---|---|---|
| 1 | Binmaneea Khalid Waleed M | member intelligence | intro, business pain, how drifting members are spotted | architecture, data and scenario layer, segmentation, churn model |
| 2 | Asiri Mohammed Yahya A | decision and optimisation | demo of the weekly workflow, headline result | case based reasoning, planning problem, genetic algorithm against CP-SAT, E3 to E5 |
| 3 | Abdulaziz Ali S Hasanain | knowledge and interaction | trust and explanation, pricing, outro | rule engine, knowledge graph, assistant, E6 to E8, degraded mode |

Each section is a list of beats. A beat is one slide state with an id such as `P2.3` (promotion) or `T3.5` (technical), an **On screen** description for the deck, and the exact **Say** narration. Each script ends with a fact sheet that traces every number to the report or to `SystemCode/notebooks/results/`. If a number in a script changes, change the fact sheet and the deck together.

Narration is about 235 words per section (never over 240) at roughly 145 words per minute. The promotion leads with strengths. The system design video states the mixed results plainly (noisy CBR estimates, the genetic algorithm losing to greedy on noisy estimates, assistant routing no better than keywords on held out questions). Keep those lines when you rehearse.

## Slides

The presentation decks live in `Video/presentation/` (built separately). They open in a browser. Press `F` for full screen, the arrow keys or space to advance, and `P` to open a presenter window with the script and a timer.

## Recording with OBS

- Record in your own voice with your webcam on. AI generated speech is not allowed (see `AGENTS.md`).
- Capture the browser window showing the deck in full screen at 1920 by 1080, 30 fps. Add your webcam as a separate source.
- Place the camera bubble in the bottom right corner. The slides keep that corner clear, so do not move it.
- Use a quiet room, a headset or a close microphone, and do a ten second test recording first. Watch the audio meter so the loudest peaks stay in the yellow, not the red.
- Close notifications and other windows. Use the presenter window on a second screen if you have one, so the script and timer are in view but not in the recording.
- Either record all three sections in one take, or record each section separately and cut them together. A separate take per section is easier to redo and each one should land near 1:40. Start each section on its first beat (`P1.1`, `P2.1`, `P3.1`) and keep a second of silence at both ends so the cuts are clean.
- Read at a natural pace. If a section runs long, drop a clause rather than speeding up. Aim for 5:00 in total, and trim a clause if a take runs over.
- Export as MP4 (H.264, AAC) and use the file names in the table above. Do not commit the files. Add the video links to this note and to the root README.

## Post-production

The recordings were edited in `Video/editing/`, which is git-ignored (recordings, exports and the helper scripts). From the OBS canvas (slides top right, the three webcams stacked on the left), each video was cropped to the 1920 by 1080 slides with only the current speaker's face in a circle in the camera corner, swapping with a short animation at each section change. Silent pauses were sped up to 2.5x, speech plays at normal speed, and the narration was levelled per speaker, cleaned up (high-pass, light denoise, EQ, de-esser, compressor) and normalised to -16 LUFS.
