#!/bin/bash
# Generate TTS voiceover clips using OpenAI's API
# Usage: ./generate-voiceovers.sh
#
# Requires OPENAI_API_KEY in .env
# Creates 31 clips (one per day of month, cycling by day number)
# IMPORTANT: Every clip must mention "infrasketch.net" explicitly

set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
source "$SCRIPT_DIR/.env"

OUT_DIR="$SCRIPT_DIR/voiceovers"
mkdir -p "$OUT_DIR"

if [ -z "${OPENAI_API_KEY:-}" ]; then
  echo "Error: OPENAI_API_KEY not set in .env"
  exit 1
fi

# Format: name|voice|text
# Voices: alloy, echo, fable, nova, onyx, shimmer
# EVERY clip says "infrasketch.net" explicitly
CLIPS=(
  # Day 1-3: Vibe coders
  '01-vibe-coder-nova|nova|Are you a vibe coder? Let an expert design your system, create a design doc, and put it in your repo so your coding agents know exactly what to build. Try it free at infrasketch.net.'
  '02-vibe-coder-onyx|onyx|Stop vibe coding your architecture. InfraSketch designs your system in seconds and generates the design doc. Drop it in your repo and let your AI agents handle the rest. infrasketch.net.'
  '03-vibe-coder-shimmer|shimmer|Your AI coding agent is only as good as the plan you give it. InfraSketch creates the architecture and the design doc. You just paste it in your repo and start building. infrasketch.net.'

  # Day 4-6: Students
  '04-student-nova|nova|Studying system design? Watch AI architect a real system in seconds, then generate a full design document you can learn from. Try it free at infrasketch.net.'
  '05-student-echo|echo|System design interviews got you stressed? InfraSketch shows you how the pros architect systems. Watch, learn, and build your own. Free to try at infrasketch.net.'
  '06-student-fable|fable|Want to learn system design the fast way? InfraSketch builds production-ready architectures in seconds and explains every decision in a design doc. Check it out at infrasketch.net.'

  # Day 7-9: Senior engineers
  '07-senior-onyx|onyx|Skip the whiteboard. InfraSketch designs production-ready architectures in seconds and generates the design doc to match. Try it free at infrasketch.net.'
  '08-senior-echo|echo|Tired of spending hours on architecture diagrams? InfraSketch generates your system design and a complete design document in under a minute. infrasketch.net.'
  '09-senior-alloy|alloy|You know the architecture in your head. InfraSketch gets it on screen in seconds, then generates the design doc your team actually needs. No more whiteboard photos. infrasketch.net.'

  # Day 10-12: General hooks
  '10-general-nova|nova|What if you could design an entire system architecture in sixty seconds? InfraSketch does it with AI. Diagram, design doc, everything. Try it free at infrasketch.net.'
  '11-general-shimmer|shimmer|From idea to architecture in seconds. InfraSketch uses AI to design your system and generate a complete design document. No whiteboard required. infrasketch.net.'
  '12-general-onyx|onyx|Most teams spend days on system design. InfraSketch does it in seconds. AI-powered architecture diagrams and full design documents. Try it free at infrasketch.net.'

  # Day 13-15: Interview prep
  '13-interview-nova|nova|Got a system design interview coming up? Watch how InfraSketch architects real systems. Study the design docs it generates. Walk in confident. infrasketch.net.'
  '14-interview-echo|echo|The fastest way to prep for system design interviews. Watch AI build the architecture, read the design doc, understand every trade-off. Try it at infrasketch.net.'
  '15-interview-fable|fable|System design rounds are the hardest part of tech interviews. InfraSketch shows you how to think about architecture. Watch, learn, and practice free at infrasketch.net.'

  # Day 16-18: Startup founders
  '16-startup-shimmer|shimmer|Building a startup? Get your architecture right from day one. InfraSketch designs your system and creates the technical design doc investors want to see. infrasketch.net.'
  '17-startup-onyx|onyx|Every startup needs a technical architecture. Most founders skip it and pay later. InfraSketch generates yours in seconds, complete with a design document. infrasketch.net.'
  '18-startup-nova|nova|You have the idea. InfraSketch builds the architecture. AI designs your system, generates the design doc, and gives you a blueprint to build on. Try it free at infrasketch.net.'

  # Day 19-21: Freelancers and consultants
  '19-freelance-echo|echo|Freelance developer? Impress your clients with professional architecture diagrams and design documents. InfraSketch generates both in under a minute. infrasketch.net.'
  '20-freelance-alloy|alloy|Consultants, stop spending hours on architecture proposals. InfraSketch creates production-ready system designs and design docs in seconds. Look like a genius. infrasketch.net.'
  '21-freelance-shimmer|shimmer|Win more contracts with professional system designs. InfraSketch generates the architecture diagram and a complete design document. Your clients will love it. infrasketch.net.'

  # Day 22-24: AI and automation angle
  '22-ai-onyx|onyx|AI can write your code. But who designs the system? InfraSketch. AI-powered architecture design with complete design documents. The missing piece of your AI workflow. infrasketch.net.'
  '23-ai-nova|nova|Cursor writes the code. InfraSketch designs the system. Together, you go from idea to production-ready architecture in minutes, not days. Try it at infrasketch.net.'
  '24-ai-fable|fable|The future of software engineering is AI-assisted. InfraSketch handles the architecture. Your coding agent handles the code. You handle the vision. infrasketch.net.'

  # Day 25-27: Speed and efficiency
  '25-speed-echo|echo|Sixty seconds. That is all it takes. InfraSketch designs your entire system architecture and generates a full design document. Watch it happen at infrasketch.net.'
  '26-speed-shimmer|shimmer|What used to take your team a full sprint now takes sixty seconds. InfraSketch generates architecture diagrams and design docs with AI. Try it free at infrasketch.net.'
  '27-speed-alloy|alloy|Architecture meetings that drag on for hours? InfraSketch generates the system design in seconds. Spend your time building, not debating boxes and arrows. infrasketch.net.'

  # Day 28-31: Bold and punchy
  '28-bold-onyx|onyx|Every great system starts with a great design. InfraSketch creates both the architecture and the documentation. All powered by AI. All in seconds. infrasketch.net.'
  '29-bold-nova|nova|You would not build a house without blueprints. Why build software without a system design? InfraSketch creates your architecture and design doc instantly. infrasketch.net.'
  '30-bold-echo|echo|The best engineers design before they code. InfraSketch makes that effortless. AI-generated architecture diagrams and design documents in seconds. infrasketch.net.'
  '31-bold-shimmer|shimmer|Ship faster. Design smarter. InfraSketch uses AI to create your system architecture and generate a complete design document. From zero to blueprint in seconds. infrasketch.net.'
)

echo "Generating ${#CLIPS[@]} voiceover clips..."
echo ""

for entry in "${CLIPS[@]}"; do
  IFS='|' read -r name voice text <<< "$entry"
  outfile="$OUT_DIR/${name}.mp3"

  if [ -f "$outfile" ]; then
    echo "  Skipping $name (already exists)"
    continue
  fi

  echo "  Generating: $name (voice: $voice)"
  curl -s -X POST "https://api.openai.com/v1/audio/speech" \
    -H "Authorization: Bearer $OPENAI_API_KEY" \
    -H "Content-Type: application/json" \
    -d "$(jq -n --arg model "tts-1-hd" --arg voice "$voice" --arg input "$text" \
      '{model: $model, voice: $voice, input: $input, response_format: "mp3"}')" \
    -o "$outfile"

  if [ -s "$outfile" ] && file "$outfile" | grep -q "Audio\|MPEG\|data"; then
    duration=$(ffprobe -v quiet -show_entries format=duration -of csv=p=0 "$outfile" 2>/dev/null || echo "unknown")
    echo "    Saved: $outfile (${duration}s)"
  else
    echo "    WARNING: $outfile may be invalid"
    cat "$outfile"
    rm -f "$outfile"
  fi
done

echo ""
echo "Done! ${#CLIPS[@]} voiceovers saved to: $OUT_DIR/"
ls -la "$OUT_DIR/"
