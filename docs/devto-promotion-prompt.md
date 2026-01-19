# DEV.to Bulk Comment Promotion Prompt

Use this prompt to have Claude automatically find and comment on 10+ DEV.to articles promoting InfraSketch:

---

## PROMPT:

Using the Chrome extension, find and comment on 10+ recent DEV.to articles about system design, architecture diagrams, or related topics. For each article:

1. **Search DEV.to** for articles published in the last 30 days with these topics:
   - "system design"
   - "architecture diagram"
   - "software architecture"
   - "infrastructure design"
   - "system design interview"
   - "microservices architecture"
   - "cloud architecture"

2. **Filter criteria:**
   - Published within last 30 days
   - Has engagement (reactions/comments)
   - Relevant to InfraSketch's value proposition

3. **For each article, post a contextual comment** that:
   - References specific content from the article
   - Naturally mentions InfraSketch (infrasketch.net)
   - Provides value (not spammy)
   - Explains how InfraSketch helps with the topic discussed

4. **Comment variations** - Use different angles:
   - For interview prep articles: "InfraSketch helps practice system design patterns by generating diagrams from descriptions"
   - For architecture articles: "InfraSketch makes it easy to experiment with different architectural approaches conversationally"
   - For diagramming articles: "InfraSketch takes a different approach - AI-powered so you describe your system and it generates the diagram"
   - For documentation articles: "InfraSketch auto-generates design documents alongside diagrams, saving documentation time"

5. **Track progress** using the todo list tool and report:
   - How many articles found
   - How many comments posted
   - Any errors or issues
   - Links to all comments posted

6. **Important guidelines:**
   - Space out comments (don't post all at once to avoid spam detection)
   - Make each comment unique and contextual
   - Only comment where genuinely relevant
   - Stop if you encounter rate limiting

Go through the entire process autonomously and provide a final summary report with all comment links.

---

## Expected Output:

A summary table with:
- Article title & link
- Comment posted (yes/no)
- Comment text used
- Engagement (likes/replies if any)
- Status (success/failed/skipped)
