import fitz
import os
import uuid


# --------------------------------------------------------------------
# Highlight issue on *page*
# --------------------------------------------------------------------
def highlight_issue_on_page(page, snippet, severity, comment_text):
    """
    Adds highlight + attached comment to a specific page.
    Fully compatible with ALL PyMuPDF versions.
    """

    color_map = {
        "high": (1, 0, 0),        # 🔴 Red
        "medium": (1, 0.6, 0),    # 🟠 Orange
        "low": (0, 0.6, 1),       # 🔵 Blue
    }

    color = color_map.get(severity, (0, 0.5, 1))

    try:
        rects = page.search_for(snippet)
    except Exception:
        return

    for rect in rects:
        try:
            annot = page.add_highlight_annot(rect)
            annot.set_colors({"stroke": color})
            annot.update()

            annot.set_info({
                "content": comment_text,
                "title": "AI Reviewer"
            })
            annot.update()

        except Exception as e:
            print(f"[ANNOTATION ERROR] {e}")
            continue


# --------------------------------------------------------------------
# Add legend on page 1
# --------------------------------------------------------------------
def add_legend(page):
    legend = """
AI ISSUE SEVERITY LEGEND

🔴 HIGH   – Critical DPR issue
🟠 MEDIUM – Needs revision
🔵 LOW    – Suggestion / advisory
"""

    rect = fitz.Rect(30, 30, 260, 160)

    page.insert_textbox(
        rect,
        legend,
        fontsize=10,
        color=(1, 1, 1),
        fill=(0, 0, 0, 0.65),  # translucent black box
    )


# --------------------------------------------------------------------
# Master function: Annotate full PDF
# --------------------------------------------------------------------
def annotate_pdf(input_path, issues):
    """
    Adds:
      - legend on first page
      - highlights
      - comments
    Produces an annotated PDF in /annotated/
    """

    doc = fitz.open(input_path)

    # --------------------------
    # Insert severity legend
    # --------------------------
    add_legend(doc[0])

    # --------------------------
    # Apply highlights for each issue
    # --------------------------
    for issue in issues:
        try:
            page_number = issue.get("page")
            snippet = issue.get("snippet", "").strip()
            severity = issue["meta"].get("severity", "low")
            comment_text = issue["meta"].get("issue", "Issue found.")

            if not snippet:
                continue

            if page_number < 0 or page_number >= len(doc):
                continue

            page = doc[page_number]
            highlight_issue_on_page(page, snippet, severity, comment_text)

        except Exception as e:
            print("[ANNOTATION ERROR]", e)
            continue

    # --------------------------
    # Save final annotated file
    # --------------------------
    os.makedirs("annotated", exist_ok=True)
    file_id = uuid.uuid4().hex
    output_path = os.path.join("annotated", f"DPR_Reviewed_{file_id}.pdf")

    doc.save(output_path, garbage=4, deflate=True, clean=True)
    doc.close()

    return output_path
