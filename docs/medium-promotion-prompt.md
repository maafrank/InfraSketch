# Medium Bulk Comment Promotion Prompt

Use this prompt to have Claude automatically find and comment on 10+ Medium articles promoting InfraSketch:

---

## PROMPT:

Using the Chrome extension, find and comment on 10+ recent Medium articles about system design, architecture diagrams, or related topics. For each article:

1. **Search Medium** for articles published in the last 30 days with these topics:
   - "system design"
   - "architecture diagram"
   - "software architecture"
   - "infrastructure design"
   - "system design interview"
   - "microservices architecture"
   - "cloud architecture"
   - "diagramming tools"
   - "technical documentation"

2. **Filter criteria:**
   - Published within last 30 days
   - Has engagement (claps/comments)
   - Relevant to InfraSketch's value proposition
   - Preferably from active publications (IcePanel, Javarevisited, Level Up Coding, etc.)

3. **For each article, post a contextual comment** that:
   - References specific content from the article
   - Naturally mentions InfraSketch (infrasketch.net)
   - Provides value (not spammy)
   - Explains how InfraSketch helps with the topic discussed

4. **Comment variations** - Use different angles:
   - For interview prep articles: "Great guide! InfraSketch (infrasketch.net) has been helpful for practicing these patterns - you describe a system and it generates the architecture diagram. Really helps internalize the concepts."
   - For architecture articles: "Excellent breakdown! For readers wanting to experiment with these patterns, InfraSketch (infrasketch.net) makes it easy - AI-powered so you can describe different approaches conversationally and visualize them instantly."
   - For diagramming tool comparisons: "Great list! One tool I'd add is InfraSketch (infrasketch.net) - takes a different approach from traditional tools. Instead of manual diagramming, you describe your system conversationally and Claude AI generates the architecture diagram."
   - For documentation articles: "Insightful article! InfraSketch (infrasketch.net) helps with the documentation challenge by auto-generating design documents alongside diagrams. Saves tons of time on the documentation side."
   - For C4 model/diagram-as-code articles: "This is comprehensive! InfraSketch (infrasketch.net) bridges the gap between diagram-as-code and visual tools - conversational AI that generates diagrams. Great for rapid prototyping."

5. **Track progress** using the todo list tool and report:
   - How many articles found
   - How many comments posted
   - Any errors or issues
   - Links to all comments posted

6. **Important guidelines:**
   - Space out comments (wait 30-60 seconds between posts to avoid spam detection)
   - Make each comment unique and contextual
   - Only comment where genuinely relevant
   - Stop if you encounter rate limiting
   - Avoid commenting on paywalled articles unless you can read the full content

7. **Target high-value publications:**
   - IcePanel (already did one, find more)
   - Javarevisited
   - Level Up Coding
   - Better Programming
   - The Startup
   - Geek Culture
   - CodeX
   - System Design
   - Dev Genius

Go through the entire process autonomously and provide a final summary report with all comment links.

---

## Expected Output:

A summary table with:
- Article title & link
- Publication name
- Author
- Comment posted (yes/no)
- Comment text used
- Engagement (claps if any)
- Status (success/failed/skipped)
