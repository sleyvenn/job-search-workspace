"""Read initial-release state values without changing user text or documents."""

LEGACY_APPLICATION_STATUS = {
    'pendiente': 'pending', 'reservada': 'reserved', 'descartada': 'discarded',
    'bloqueada': 'blocked', 'incierta': 'uncertain', 'enviada': 'sent',
    'apartada': 'aside', 'cerrada': 'closed',
}
LEGACY_DECISION = {
    'pendiente': 'pending', 'priorizar': 'prioritize', 'revisar': 'review',
    'reservar': 'reserve', 'descartar': 'discard',
}
LEGACY_CV_REVIEW = {'pendiente': 'pending', 'aprobado': 'approved', 'cambios': 'changes'}


def normalize_application_status(value):
    return LEGACY_APPLICATION_STATUS.get(value, value) if isinstance(value, str) else None


def normalize_decision(value):
    return LEGACY_DECISION.get(value, value) if isinstance(value, str) else None


def normalize_cv_review(value):
    return LEGACY_CV_REVIEW.get(value, value) if isinstance(value, str) else None


def normalize_catalog(state):
    for job in state.get('jobs', []):
        application = job.get('application', {})
        if 'status' in application:
            application['status'] = normalize_application_status(application['status'])
        if 'decision' in job:
            job['decision'] = normalize_decision(job['decision'])
    return state


def normalize_reviews(reviews):
    for item in [*reviews.get('jobs', {}).values(), *reviews.get('history', [])]:
        if 'decision' in item:
            item['decision'] = normalize_decision(item['decision'])
        if 'cv_review' in item:
            item['cv_review'] = normalize_cv_review(item['cv_review'])
    return reviews
