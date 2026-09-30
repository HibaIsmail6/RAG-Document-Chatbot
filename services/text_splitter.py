import re

SECTION_HEADINGS = [
    "EDUCATION",
    "TECHNICAL SKILLS",
    "PROJECTS",
    "CERTIFICATIONS"
]

PROJECT_NAMES = [
    "Signature Forgery Detector",
    "RAG Document Chatbot",
    "AI Language Translator",
    "Intranet Virtual Whiteboard"
]


def split_text(pages: list[dict]) -> list[dict]:
    chunks = []

    for page in pages:
        text = page["text"]
        page_number = page["page"]

        section_pattern = r"\b(" + "|".join(
            map(re.escape, SECTION_HEADINGS)
        ) + r")\b"

        section_matches = list(
            re.finditer(
                section_pattern,
                text,
                re.IGNORECASE
            )
        )

        # -----------------------------------------
        # CASE 1: Recognized sections found
        # -----------------------------------------
        if section_matches:

            for i, section_match in enumerate(section_matches):

                section_name = section_match.group(1).upper()

                start = section_match.start()

                end = (
                    section_matches[i + 1].start()
                    if i + 1 < len(section_matches)
                    else len(text)
                )

                section_text = text[start:end].strip()

                # Special handling for PROJECTS
                if section_name == "PROJECTS":

                    project_pattern = r"(" + "|".join(
                        map(re.escape, PROJECT_NAMES)
                    ) + r")"

                    project_matches = list(
                        re.finditer(
                            project_pattern,
                            section_text,
                            re.IGNORECASE
                        )
                    )

                    if project_matches:

                        for j, project_match in enumerate(project_matches):

                            project_start = project_match.start()

                            project_end = (
                                project_matches[j + 1].start()
                                if j + 1 < len(project_matches)
                                else len(section_text)
                            )

                            project_text = section_text[
                                project_start:project_end
                            ].strip()

                            if project_text:
                                chunks.append({
                                    "text": project_text,
                                    "page": page_number,
                                    "section": "PROJECTS",
                                    "project": project_match.group(1)
                                })

                    else:
                        # Projects section exists but project names
                        # aren't recognized
                        chunks.append({
                            "text": section_text,
                            "page": page_number,
                            "section": "PROJECTS"
                        })

                else:

                    if section_text:
                        chunks.append({
                            "text": section_text,
                            "page": page_number,
                            "section": section_name
                        })

        # -----------------------------------------
        # CASE 2: No recognized sections found
        # -----------------------------------------
        else:

            # Split arbitrary documents into smaller chunks
            words = text.split()

            chunk_size = 150
            overlap = 30

            start = 0

            while start < len(words):

                end = start + chunk_size

                chunk_words = words[start:end]

                if chunk_words:
                    chunks.append({
                        "text": " ".join(chunk_words),
                        "page": page_number,
                        "section": "GENERAL"
                    })

                start += chunk_size - overlap

    return chunks