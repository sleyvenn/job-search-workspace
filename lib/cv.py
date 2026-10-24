"""Render a CV from reviewed, source-linked content. No text generation occurs here."""
from __future__ import annotations
from pathlib import Path
from tempfile import TemporaryDirectory
from xml.sax.saxutils import escape

from .workspace import WorkspaceError, read


def validate_content(candidate, content):
    facts={fact['id']:fact for fact in candidate.get('facts',[]) if fact.get('verified') is True}
    claims=[content.get('headline'), content.get('summary')]
    for section in content.get('sections',[]):
        if not section.get('title') or not section.get('items'):
            raise WorkspaceError('Each section needs a title and content.')
        claims.extend(section['items'])
    if not claims or not content.get('sections'):
        raise WorkspaceError('CV content is missing.')
    for claim in claims:
        if not isinstance(claim,dict) or not isinstance(claim.get('text'),str) or not claim['text'].strip():
            raise WorkspaceError('Each claim needs text and references to profile facts.')
        refs=claim.get('source_refs',[])
        if not refs or any(ref not in facts for ref in refs):
            raise WorkspaceError('The CV references unconfirmed or missing facts.')
    return len(claims)


def render(candidate, content, destination):
    validate_content(candidate,content)
    try:
        from reportlab.lib import colors
        from reportlab.lib.enums import TA_LEFT
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.styles import ParagraphStyle
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, KeepTogether
    except ImportError:
        raise WorkspaceError('Install the PDF generator: python -m pip install -r requirements-pdf.txt') from None
    if not candidate.get('name'):
        raise WorkspaceError('Enter the actual candidate name before creating a CV.')
    styles={
        'name':ParagraphStyle('name',fontName='Helvetica-Bold',fontSize=23,leading=27,textColor=colors.HexColor('#172d37'),spaceAfter=6),
        'headline':ParagraphStyle('headline',fontName='Helvetica-Bold',fontSize=11,leading=15,spaceAfter=7),
        'contact':ParagraphStyle('contact',fontName='Helvetica',fontSize=9,leading=13,textColor=colors.HexColor('#4c5b63'),spaceAfter=18),
        'body':ParagraphStyle('body',fontName='Helvetica',fontSize=10,leading=15,spaceAfter=8,alignment=TA_LEFT),
        'section':ParagraphStyle('section',fontName='Helvetica-Bold',fontSize=11,leading=16,spaceBefore=13,spaceAfter=7,textColor=colors.HexColor('#172d37'),keepWithNext=True),
    }
    text=lambda s:escape(s).replace('\n','<br/>')
    contact=' · '.join(str(candidate.get(k,'')) for k in ['location','email','phone','website'] if candidate.get(k))
    story=[Paragraph(text(candidate['name']),styles['name']),
           Paragraph(text(content['headline']['text']),styles['headline']),
           Paragraph(text(contact),styles['contact']),Paragraph(text(content['summary']['text']),styles['body'])]
    for section in content['sections']:
        story.append(Paragraph(text(section['title']),styles['section']))
        for item in section['items']:
            story.append(Paragraph(text(item['text']),styles['body']))
    document=SimpleDocTemplate(str(destination),pagesize=A4,leftMargin=43,rightMargin=43,topMargin=39,bottomMargin=39,
                               title=candidate['name']+' - '+content['headline']['text'],author=candidate['name'])
    document.build(story)


def create(workspace, identifier, content, tailoring, language='es'):
    workspace.job(identifier)
    candidate=read(workspace.root/'candidate.json')
    with TemporaryDirectory(prefix='job-workspace-cv-') as tmp:
        output=Path(tmp)/'cv.pdf'
        render(candidate,content,output)
        return workspace.register_cv(identifier,output,tailoring,language,content)
