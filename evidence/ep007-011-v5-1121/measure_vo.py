#!/usr/bin/env python3
"""Measure edge-tts duration for each planned v5 voice part (en +5%, ko +3%)."""
import subprocess, sys, os, wave, tempfile, re

KO = "ko-KR-InJoonNeural"
EN = "en-US-AndrewMultilingualNeural"
TRIM = ("silenceremove=start_periods=1:start_threshold=-45dB:start_silence=0.04,"
        "areverse,silenceremove=start_periods=1:start_threshold=-45dB:start_silence=0.04,areverse")
FF = sys.argv[1] if len(sys.argv) > 1 else "ffmpeg"

PLAN = {
 "ep009": [
   ("hook", [("en","Koreans leave their laptop here. Nobody steals it.")]),
   ("s1", [("en","Cafés here are full of students doing"),("ko","카공"),("en","— café study, for hours.")]),
   ("s2", [("en","Cameras are everywhere, and everyone is doing the same thing.")]),
   ("bonus", [("en","Some even leave their phone to save the seat.")]),
   ("cta", [("en","Would your laptop survive ten minutes here? Yes or no?")]),
 ],
 "ep011": [
   ("hook", [("en","Empty seat. Crowded train. Nobody sits.")]),
   ("s1", [("en","The pink seats are saved for pregnant women.")]),
   ("s2", [("en","The train can be packed, and people still stand.")]),
   ("bonus", [("en","Most people just keep it empty, all day.")]),
   ("cta", [("en","Would you sit there? Yes or no?")]),
 ],
 "ep008": [
   ("hook", [("en","Dinner for four dollars, inside a convenience store.")]),
   ("s1", [("en","After work, people walk into a"),("ko","편의점"),("en","— a convenience store.")]),
   ("s2", [("en","Grab kimbap or ramyeon, heat it, and eat by the window.")]),
   ("bonus", [("en","Hot water for cup noodles is free.")]),
   ("cta", [("en","Dinner at a convenience store — would you? Yes or no?")]),
 ],
 "ep010": [
   ("hook", [("en","Sleep here all night for about ten dollars.")]),
   ("s1", [("en","It's a"),("ko","찜질방"),("en","— a Korean sauna open all night.")]),
   ("s2", [("en","Hot rooms, a big floor, and everyone wears the same clothes.")]),
   ("bonus", [("en","The classic snack is baked eggs and sweet rice drink.")]),
   ("cta", [("en","Would you sleep on a floor with strangers? Yes or no?")]),
 ],
 "ep007": [
   ("hook", [("en","One Korean word for pain, shock, and tired.")]),
   ("s1", [("en","Back pain, bad news, or just standing up — one word.")]),
   ("s2", [("en","Drop your phone. Hear bad news. Sit down after work.")]),
   ("bonus", [("en","After thirty, you say it every time you stand up.")]),
   ("cta", [("en","Do you have a word like this? Yes or no?")]),
 ],
}

def dur(p):
    with wave.open(p) as w:
        return w.getnframes()/w.getframerate()

d = tempfile.mkdtemp()
for ep, scenes in PLAN.items():
    tot = 0.0
    print(f"=== {ep}")
    for name, parts in scenes:
        n = 0.0
        for j,(lang,txt) in enumerate(parts):
            mp3 = os.path.join(d, f"{ep}_{name}_{j}.mp3")
            wav = os.path.join(d, f"{ep}_{name}_{j}.wav")
            voice = KO if lang=="ko" else EN
            rate = "+3%" if lang=="ko" else "+5%"
            r = subprocess.run([sys.executable,"-m","edge_tts","--voice",voice,f"--rate={rate}",
                                "--text",txt,"--write-media",mp3],capture_output=True,text=True)
            if r.returncode: print("  FAIL", ep, name, r.stderr[-200:]); continue
            subprocess.run([FF,"-y","-loglevel","error","-i",mp3,"-af",TRIM,"-ac","1","-ar","44100",wav])
            n += dur(wav)
        n += 0.12*(len(parts)-1)
        print(f"  {name:6s} {n:.2f}s")
        tot += max(n, 0)
    print(f"  voice total {tot:.2f}s")
