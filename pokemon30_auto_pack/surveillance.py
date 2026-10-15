#!/usr/bin/env python3
"""Surveillance prudente de pages produits Pokémon 30 ans.

Aucune promesse d'accès aux stocks : les sites protégés/dynamiques restent « non vérifiables ».
Des alertes ne partent que pour disponibilité livraison + prix explicite sous le seuil.
"""
from __future__ import annotations

import json
import logging
import os
import re
import time
import unicodedata
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse
from urllib.robotparser import RobotFileParser

import requests
from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parent
UA = 'Pokemon30PriceWatcher/1.0 (non-commercial; contact: repository-owner)'
HEADERS = {'User-Agent': UA, 'Accept-Language': 'fr-FR,fr;q=0.9,en;q=0.4'}
log = logging.getLogger('pokemon30')
logging.basicConfig(level=logging.INFO, format='%(levelname)s %(message)s')

STATUS_LABELS = {
    'available': 'En stock (livraison probable)',
    'out': 'Rupture',
    'preorder': 'Précommande',
    'upcoming': 'À venir',
    'store': 'Magasin uniquement',
    'unknown': 'Non vérifiable',
}


def normal(text: str) -> str:
    text = unicodedata.normalize('NFKD', text or '')
    return ''.join(c for c in text if not unicodedata.combining(c)).lower()


def money_value(v):
    if isinstance(v, (int, float)) and 1 <= float(v) <= 2000:
        return round(float(v), 2)
    if v is None:
        return None
    val = str(v).replace('\u202f', '').replace('\xa0', '').replace(' ', '').replace(',', '.').replace('€', '')
    if not re.fullmatch(r'\d{1,4}(?:\.\d{1,2})?', val):
        return None
    n = float(val)
    return round(n, 2) if 1 <= n <= 2000 else None


def ld_products(soup):
    for script in soup.find_all('script', type='application/ld+json'):
        raw = (script.string or script.get_text() or '').strip()
        if not raw:
            continue
        try:
            obj = json.loads(raw)
        except (ValueError, TypeError):
            continue
        queue = obj if isinstance(obj, list) else [obj]
        while queue:
            item = queue.pop(0)
            if not isinstance(item, dict):
                continue
            typ = item.get('@type') or ''
            types = [typ] if isinstance(typ, str) else typ
            if 'Product' in types:
                yield item
            for key in ('@graph', 'mainEntity', 'itemListElement'):
                more = item.get(key) or []
                queue.extend(more if isinstance(more, list) else [more])


def relevant(title: str, product_id: str) -> bool:
    t = normal(title)
    keys = {
        'bundle': ('bundle', 'lot de boosters'),
        'etb': ('dresseur', 'elite', 'etb'),
        'mini': ('mini',),
        'exnym': ('nymphali',),
        'examph': ('amphinobi',),
        'classeur': ('classeur',),
        'mentali': ('mentali',),
        'mewtwo': ('mewtwo',),
        'mew': ('mew',),
        'evoli': ('evoli',),
        'poster': ('poster','sulfura'),
        'stickluc': ('lucario',),
        'sticknoa': ('noadkoko',),
        'noctali': ('noctali',),
        'boxnym': ('nymphali',),
        'boxamph': ('amphinobi',),
    }
    return 'pokemon' in t and any(k in t for k in keys.get(product_id, (product_id,)))


def extract(html: str, link: dict) -> dict:
    soup = BeautifulSoup(html, 'html.parser')
    title_node = soup.find('h1')
    title = title_node.get_text(' ', strip=True) if title_node else (soup.title.get_text(' ', strip=True) if soup.title else '')
    base = {'status': 'unknown', 'price': None, 'reason': 'Signaux insuffisants', 'title': title[:180]}
    if not relevant(title, link['product_id']):
        base['reason'] = 'Titre produit absent ou incohérent (protection, redirection ou page erronée)'
        return base

    # Text following product H1 excludes navigation and merchandising preceding the product.
    all_text = soup.get_text(' ', strip=True)
    lead = all_text.find(title)
    content = all_text[max(lead, 0):] if lead >= 0 else all_text
    text = normal(content)
    domain = urlparse(link['url']).netloc.lower()

    # Price from product structured data is preferred to generic number matching.
    availability = ''
    for obj in ld_products(soup):
        if not relevant(str(obj.get('name', '')), link['product_id']):
            continue
        rawoffers = obj.get('offers') or []
        rawoffers = rawoffers if isinstance(rawoffers, list) else [rawoffers]
        for off in rawoffers:
            if not isinstance(off, dict):
                continue
            base['price'] = money_value(off.get('price') or off.get('lowPrice')) or base['price']
            availability = str(off.get('availability') or '').lower() or availability
        if base['price'] is not None:
            break

    if base['price'] is None:
        # Product price near title only, exclude suggestions and shipping prices far below.
        head = content[:2000]
        # Playin places unrelated recommendation prices immediately after the H1.
        for separator in ('Vous aimerez aussi', 'Meilleures ventes', 'DESCRIPTION complète'):
            head = head.split(separator, 1)[0]
        prices = re.findall(r'(?<!\d)(\d{1,3}(?:[\s\u00a0\u202f]\d{3})*(?:[,.]\d{2}))\s*€', head)
        # First displayed euro amount is most plausibly the product price.
        base['price'] = money_value(prices[0]) if prices else None

    # Explicit shop-specific shipping status beats structured metadata (often stale).
    if 'play-in.com' in domain:
        if re.search(r'livraison indisponible|rupture temporaire en livraison', text):
            base.update(status='out', reason='Playin : rupture en livraison')
            return base
        if 'retrait magasin uniquement' in text:
            base.update(status='store', reason='Playin : retrait uniquement en magasin')
            return base
    if 'ultrajeux.com' in domain:
        if re.search(r'disponible en magasin', text):
            base.update(status='store', reason='UltraJeux : stock magasin, livraison non confirmée')
            return base
    if 'philibertnet.com' in domain:
        # Some items are open for preorders long after original release.
        if re.search(r'precommander|precommande\s*:', text[:2400]):
            base.update(status='preorder', reason='Philibert : précommande')
            return base
        if re.search(r'a venir\s*:', text[:1500]):
            base.update(status='upcoming', reason='Philibert : à venir')
            return base

    if re.search(r'en precommande|prix bientot disponible', text[:1700]):
        base.update(status='preorder', reason='Précommande ou prix non encore publié')
        return base

    # Strong stock/availability negatives before vague Add to cart text.
    if re.search(r'rupture de stock|en rupture de stock|rupture temporaire|indisponible en livraison|non disponible', text[:9000]):
        base.update(status='out', reason='Rupture indiquée sur la fiche')
        return base
    if 'preorder' in availability or 'presale' in availability:
        base.update(status='preorder', reason='Disponibilité structurée : précommande')
        return base
    if 'outofstock' in availability or 'soldout' in availability:
        base.update(status='out', reason='Disponibilité structurée : rupture')
        return base
    if 'instock' in availability or 'limitedavailability' in availability:
        base.update(status='available', reason='Disponibilité structurée : en stock')
        return base

    # Avoid misreading a purchase button from recommendations further down the page.
    near_title = normal(content[:1700].split('Vous aimerez aussi', 1)[0].split('Meilleures ventes', 1)[0])
    if re.search(r'ajouter au panier|add to cart', near_title):
        base.update(status='available', reason='Bouton panier affiché sur la fiche (à confirmer au paiement)')
        return base
    base['reason'] = 'Stock en ligne non certifié (site dynamique ou informations ambiguës)'
    return base


def fetch(session, link):
    try:
        r = session.get(link['url'], headers=HEADERS, timeout=(8, 18), allow_redirects=True)
        if r.status_code == 429:
            return {'status': 'unknown', 'price': None, 'reason': 'Trop de requêtes (HTTP 429)'}
        if r.status_code in (403, 401):
            return {'status': 'unknown', 'price': None, 'reason': f'Accès bloqué (HTTP {r.status_code})'}
        if r.status_code != 200:
            return {'status': 'unknown', 'price': None, 'reason': f'Erreur HTTP {r.status_code}'}
        if len(r.content) < 900:
            return {'status': 'unknown', 'price': None, 'reason': 'Page incomplète'}
        return extract(r.text, link)
    except requests.RequestException as exc:
        return {'status': 'unknown', 'price': None, 'reason': 'Erreur réseau : ' + type(exc).__name__}


def should_alert(now: dict, prior: dict, max_price: float):
    """Unknown does not reset the last confirmed eligibility; prevents repeat alerts on blocking."""
    previous = bool(prior.get('eligible_state', False))
    if now.get('status') == 'unknown':
        return False, previous
    eligible = (now.get('status') == 'available' and now.get('price') is not None
                and now['price'] <= max_price)
    return bool(eligible and not previous), eligible


def notify(topic: str, product: dict, link: dict, offer: dict):
    if not re.fullmatch(r'[A-Za-z0-9_-]{16,64}', topic):
        log.error('NTFY_TOPIC doit contenir de 16 à 64 caractères [A-Za-z0-9_-].')
        return False
    msg = f"{product['name']} chez {link['shop']} : {offer['price']:.2f} € (plafond {product['max_price']:.2f} €). Vérifie le panier et la livraison.\n{link['url']}"
    try:
        response = requests.post(
            'https://ntfy.sh/' + topic,
            data=msg.encode('utf-8'),
            headers={'Title': 'Pokémon 30 ans : stock repéré', 'Priority': 'high', 'Tags': 'shopping_cart', 'Click': link['url']},
            timeout=12,
        )
        response.raise_for_status()
        return True
    except requests.RequestException as exc:
        log.error('Notification échouée : %s', type(exc).__name__)
        return False


def run():
    cfg = json.loads((ROOT / 'produits.json').read_text(encoding='utf-8'))
    file = ROOT / 'offres.json'
    old = json.loads(file.read_text(encoding='utf-8')) if file.exists() else {}
    previous = {i['id']: i for i in old.get('offers', [])}
    products = {p['id']: p for p in cfg['products']}
    checked = datetime.now(timezone.utc).isoformat(timespec='seconds')
    topic = os.getenv('NTFY_TOPIC', '').strip()
    demo = os.getenv('MOCK_MODE') == '1'
    session = requests.Session()
    results = []
    for idx, link in enumerate(cfg['links']):
        past = previous.get(link['id'], {})
        raw = {'status': 'unknown', 'price': None, 'reason': 'Mode test'} if demo else fetch(session, link)
        record = {'id': link['id'], 'product_id': link['product_id'], 'status': raw['status'], 'price': raw.get('price'),
                  'reason': raw.get('reason', ''), 'checked_at': checked}
        if 'title' in raw:
            record['title'] = raw['title']
        prod = products[link['product_id']]
        alert, state = should_alert(record, past, float(prod['max_price']))
        # Without notifications configured, maintain state but do not imply an alert was sent.
        if alert and topic:
            ok = notify(topic, prod, link, record)
            if not ok:
                state = False  # Retry on next eligible check if the push failed.
            else:
                log.info('ALERTE : %s chez %s', prod['name'], link['shop'])
        record['eligible_state'] = state
        results.append(record)
        log.info('%-30s %-31s %-10s %s', prod['name'][:30], link['shop'][:31], record['status'], record['price'])
        if not demo and idx + 1 < len(cfg['links']):
            time.sleep(1.5)  # Restrained request rate; no parallel requests to stores.
    file.write_text(json.dumps({'checked_at': checked, 'offers': results, 'note': 'Statuts détectés automatiquement : confirmation requise sur la boutique.'},
                               ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    log.info('Contrôle terminé : %s liens, %s confirmés disponibles.', len(results), sum(o['status'] == 'available' for o in results))


if __name__ == '__main__':
    run()
