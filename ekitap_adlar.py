"""E-kitap araması için Türkçe kitap/yazar adı -> Project Gutenberg'in tanıdığı (çoğunlukla İngilizce) arama terimi.
Gutendex Türkçe adı tanımaz ("Savaş ve Barış" -> 0 sonuç); bu tablo yaygın klasikleri ve telifi bitmiş yazarları eşler. Anahtarlar katlanmış ASCII'dir."""
import re

_TR = str.maketrans("çğıöşüâîûÇĞİÖŞÜ", "cgiosuaiuCGIOSU")


def fold(s: str) -> str:
    s = s.translate(_TR).lower()
    s = re.sub(r"['’]\w*", "", s)
    s = re.sub(r"[^a-z0-9 ]", " ", s)
    return " ".join(s.split())


_TITLES = {
    "savaş ve barış": "war and peace", "anna karenina": "anna karenina", "diriliş": "resurrection tolstoy", "ivan ilyiç'in ölümü": "death of ivan ilyitch",
    "hacı murat": "hadji murad", "kreutzer sonat": "kreutzer sonata", "çocukluk": "childhood boyhood youth tolstoy",
    "suç ve ceza": "crime and punishment", "karamazov kardeşler": "brothers karamazov", "budala": "the idiot dostoyevsky", "ecinniler": "demons dostoyevsky",
    "yeraltından notlar": "notes from the underground", "beyaz geceler": "white nights dostoyevsky", "ezilenler": "the insulted and injured", "kumarbaz": "the gambler dostoyevsky",
    "ölü canlar": "dead souls", "palto": "the overcoat gogol", "müfettiş": "the inspector general", "babalar ve oğullar": "fathers and sons", "oblomov": "oblomov",
    "yüzbaşının kızı": "the captain's daughter", "vişne bahçesi": "the cherry orchard", "martı": "the seagull chekhov", "kaştanka": "chekhov",
    "sefiller": "les miserables", "notre dame'ın kamburu": "hunchback of notre dame", "monte kristo kontu": "count of monte cristo", "üç silahşörler": "three musketeers",
    "demir maskeli adam": "man in the iron mask", "madame bovary": "madame bovary", "madam bovary": "madame bovary", "kızıl ve kara": "the red and the black",
    "goriot baba": "father goriot", "germinal": "germinal", "nana": "nana zola", "kamelyalı kadın": "camille dumas", "kızıl zambak": "lily of the valley balzac",
    "gurur ve önyargı": "pride and prejudice", "akıl ve duyarlılık": "sense and sensibility", "emma": "emma austen", "jane eyre": "jane eyre", "uğultulu tepeler": "wuthering heights",
    "büyük umutlar": "great expectations", "oliver twist": "oliver twist", "iki şehrin hikayesi": "a tale of two cities", "noel şarkısı": "a christmas carol", "david copperfield": "david copperfield",
    "moby dick": "moby dick", "tom sawyer": "adventures of tom sawyer", "huckleberry finn": "huckleberry finn", "prens ve dilenci": "prince and the pauper",
    "define adası": "treasure island", "dr jekyll": "jekyll and hyde", "jekyll ve hyde": "jekyll and hyde", "dracula": "dracula", "frankenstein": "frankenstein",
    "dorian gray": "picture of dorian gray", "alice harikalar diyarında": "alice's adventures in wonderland", "alice": "alice's adventures in wonderland", "peter pan": "peter pan",
    "sherlock holmes": "sherlock holmes", "dönüşüm": "metamorphosis kafka", "dava": "the trial kafka", "şato": "the castle kafka", "hamlet": "hamlet", "romeo ve juliet": "romeo and juliet",
    "macbeth": "macbeth", "othello": "othello", "kral lear": "king lear", "bir yaz gecesi rüyası": "midsummer night's dream", "venedik taciri": "merchant of venice",
    "ilyada": "iliad homer", "odysseia": "odyssey homer", "odisea": "odyssey homer", "ilahi komedya": "divine comedy", "don kişot": "don quixote", "faust": "faust goethe",
    "genç werther'in acıları": "sorrows of young werther", "devlet": "republic plato", "prens": "the prince machiavelli", "hükümdar": "the prince machiavelli",
    "dünyanın merkezine yolculuk": "journey to the centre of the earth", "yirmi bin fersah": "twenty thousand leagues under the sea", "seksen günde devri alem": "around the world in eighty days",
    "gizemli ada": "mysterious island verne", "robinson crusoe": "robinson crusoe", "gulliver'in gezileri": "gulliver's travels", "zamanın makinesi": "the time machine",
    "dünyalar savaşı": "the war of the worlds", "görünmez adam": "the invisible man", "tarzan": "tarzan of the apes", "vahşetin çağrısı": "call of the wild",
    "zenda tutsağı": "prisoner of zenda", "küçük kadınlar": "little women", "heidi": "heidi", "pollyanna": "pollyanna", "yeşilin kızı anne": "anne of green gables",
    "böyle buyurdu zerdüşt": "thus spake zarathustra", "kapital": "capital marx", "türlerin kökeni": "origin of species", "sanat": "art of war sun tzu", "savaş sanatı": "art of war sun tzu",
    "decameron": "decameron", "binbir gece": "arabian nights", "grimm masalları": "grimm fairy tales", "andersen masalları": "andersen fairy tales", "ezop masalları": "aesop fables",
}
_AUTHORS = {
    "dostoyevski": "dostoyevsky", "dostoyevsky": "dostoyevsky", "tolstoy": "tolstoy", "çehov": "chekhov", "gogol": "gogol", "turgenyev": "turgenev", "puşkin": "pushkin",
    "lermontov": "lermontov", "gorki": "gorky", "viktor hugo": "hugo victor", "victor hugo": "hugo victor", "dumas": "dumas", "balzac": "balzac", "zola": "zola", "flaubert": "flaubert",
    "stendhal": "stendhal", "jules verne": "verne jules", "moliere": "moliere", "voltaire": "voltaire", "rousseau": "rousseau", "maupassant": "maupassant", "dickens": "dickens",
    "jane austen": "austen jane", "bronte": "bronte", "shakespeare": "shakespeare", "kafka": "kafka", "goethe": "goethe", "schiller": "schiller", "nietzsche": "nietzsche",
    "oscar wilde": "wilde oscar", "edgar allan poe": "poe edgar allan", "poe": "poe edgar allan", "mark twain": "twain mark", "conan doyle": "doyle arthur conan", "lovecraft": "lovecraft",
    "h g wells": "wells h g", "wells": "wells h g", "stevenson": "stevenson robert louis", "swift": "swift jonathan", "defoe": "defoe", "cervantes": "cervantes", "homeros": "homer",
    "dante": "dante", "platon": "plato", "aristoteles": "aristotle", "machiavelli": "machiavelli", "marx": "marx karl", "darwin": "darwin", "freud": "freud", "tolstoi": "tolstoy",
    "thomas hardy": "hardy thomas", "joseph conrad": "conrad joseph", "jack london": "london jack", "hans christian andersen": "andersen", "grimm": "grimm", "ezop": "aesop",
    "sofokles": "sophocles", "euripides": "euripides", "herodot": "herodotus", "tukididdes": "thucydides", "marcus aurelius": "marcus aurelius", "seneca": "seneca", "kant": "kant",
    "spinoza": "spinoza", "descartes": "descartes", "schopenhauer": "schopenhauer", "ibsen": "ibsen", "strindberg": "strindberg", "knut hamsun": "hamsun", "tagore": "tagore",
}
TITLES = {fold(k): v for k, v in _TITLES.items()}
AUTHORS = {fold(k): v for k, v in _AUTHORS.items()}


def lookup(q: str):
    """Sorgudaki Türkçe kitap/yazar adını Gutenberg arama terimine çevirir. (terim, 'kitap'|'yazar') ya da None."""
    f = " " + fold(q) + " "
    for k in sorted(TITLES, key=len, reverse=True):
        if " " + k + " " in f or (len(k) > 6 and " " + k in f):
            return TITLES[k], "kitap"
    for k in sorted(AUTHORS, key=len, reverse=True):
        if " " + k + " " in f or (len(k) > 6 and " " + k in f):
            return AUTHORS[k], "yazar"
    return None
