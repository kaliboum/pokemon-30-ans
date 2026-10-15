import unittest
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from surveillance import extract, should_alert, money_value


def link(pid, domain):
    return {'id': 'x', 'product_id': pid, 'url': f'https://{domain}/produit'}


def html(title, content, schema=''):
    return f'<html><head><title>{title}</title></head><body><main><h1>{title}</h1>{content}</main>{schema}</body></html>'


class Checks(unittest.TestCase):
    def test_playin_rupture_is_not_stock(self):
        v = html('Bundle 6 boosters Pokémon : 30 Ans - FR', '<p>Prix en magasin indisponible</p><p>Vous aimerez aussi 159,00 €</p><p>Livraison indisponible</p><p>Rupture temporaire en livraison</p>')
        r = extract(v, link('bundle', 'www.play-in.com'))
        self.assertEqual(r['status'], 'out')
        self.assertIsNone(r['price'])

    def test_philibert_preorder_is_not_stock(self):
        v = html('Pokémon 30 ans - Bundle 6 Boosters', '<div>Précommande : Octobre 49,95€ <button>Précommander</button></div>')
        r = extract(v, link('bundle', 'www.philibertnet.com'))
        self.assertEqual(r['status'], 'preorder')
        self.assertEqual(r['price'], 49.95)

    def test_ultrajeux_store_not_shipping(self):
        v = html('Pokémon - Bundle de 6 Boosters - 30e Anniversaire', '<p>69,90 € Disponible en Magasin</p><p>Livraison à partir de 1,80 EUR</p>')
        r = extract(v, link('bundle', 'www.ultrajeux.com'))
        self.assertEqual(r['status'], 'store')

    def test_parkage_rupture_with_add_button(self):
        v = html('Coffret Pokémon Bundle Booster - 30ᵉ Anniversaire', '<p>74,90 €</p><button>Ajouter au panier</button><p>Rupture de stock*</p>')
        self.assertEqual(extract(v, link('bundle', 'www.parkage.com'))['status'], 'out')

    def test_smyths_in_stock(self):
        v = html('Pokémon - Bundle 6 Boosters 30ème Anniversaire', '<p>35,99€ Livraison à domicile</p><button>Ajouter au panier</button>')
        r = extract(v, link('bundle', 'www.smythstoys.com'))
        self.assertEqual(r['status'], 'available')
        self.assertEqual(r['price'], 35.99)

    def test_blocked_page_has_no_stock(self):
        v = html('Access denied', '<p>Ajouter au panier 35,99 €</p>')
        self.assertEqual(extract(v, link('bundle', 'www.parkage.com'))['status'], 'unknown')

    def test_metadata_instock(self):
        ld = '<script type="application/ld+json">{"@type":"Product","name":"Pokemon bundle 6 boosters", "offers":{"@type":"Offer","price":"36.99","availability":"https://schema.org/InStock"}}</script>'
        v = html('Pokémon Bundle 6 boosters - 30 ans', '<p>Découvrez le produit</p>', ld)
        r = extract(v, link('bundle', 'www.smythstoys.com'))
        self.assertEqual(r['status'], 'available')
        self.assertEqual(r['price'], 36.99)

    def test_alert_only_eligible_and_new(self):
        now = {'status': 'available', 'price': 37.99}
        self.assertEqual(should_alert(now, {}, 39.99), (True, True))
        self.assertEqual(should_alert(now, {'eligible_state': True}, 39.99), (False, True))
        self.assertEqual(should_alert({'status': 'out', 'price': None}, {'eligible_state': True}, 39.99), (False, False))
        self.assertEqual(should_alert({'status': 'unknown', 'price': None}, {'eligible_state': True}, 39.99), (False, True))
        self.assertEqual(should_alert({'status': 'available', 'price': 49.99}, {}, 39.99), (False, False))
        self.assertEqual(should_alert({'status': 'available', 'price': None}, {}, 39.99), (False, False))

if __name__ == '__main__': unittest.main()
