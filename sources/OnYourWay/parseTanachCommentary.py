# -*- coding: utf-8 -*-

import tools
import sys

args = sys.argv

do_post = len(args) > 1 and args[1].lower() == 'post'

api_key_file = "API.key"
api_key = tools.readApiKey(api_key_file) #Add your API key
#server = 'dev.sefaria.org'
server = 'dev.sefaria.org'
sourcedir = '../OnYourWay/xml'

# Figured out by looking at the OYW app preferences, grepping for pid in 
# xml files, then comparing dibur hamatchils with the ones in the app
commentary_names = {
    # Parshanei Torah
    1:	'Onkelos',
    2:	'Targum Yonatan',
    3:	'Rashi',
    28:	'Siftei Chakhamim',
    4:	'Ramban',
    5:	'Ibn Ezra',
    6:	'Sforno',
    7:	'Baal HaTurim',
    8:	'Or HaChayim',
    9:	'Torah Temimah',
    29:	'Kli Yakar',
    # Parshanei Nach
    10:	'Metsudat David',
    11:	'Metsudat Tsion',
    12:	'Ralbag',
    30: 'Malbim Beiur Tochen',
    31: 'Malbim Peirush HaMilot',
    # Parshanei Mishna
    14:	'Rav Ovadia Mibartenura',
    15:	'Tosefot Yom Tov',
    # Parshanei Gemara
    17:	'Rashi (Gemara)',
    18:	'Tosafot',
    # Parshanei Shulchan Aruch
    20:	'Mishnah  Brurah',
    21:	'Beiur Halakha',
    # Parshanei Hazohar
    23:	'Zohar Meturgam'
}
# Sefaria already has Onkelos and Targum.
# Also, they're stored as [chapter[verse]] not [chap[verse[comment]]].
# So let's just ignore them
del commentary_names[1]; del commentary_names[2];

# TODO when we add Nach, don't put "Torah" in as a category
books = [
        ['Genesis','1'],
#        ['Exodus','2'],
#        ['Leviticus','3'],
#        ['Numbers','4'],
#        ['Deuteronomy','5']
]

# TEST TRANSLATIONS
commentary_names = { 7: 'Baal HaTurim' } # OVERRIDE
#commentary_names = { 8: 'Or HaChayim' } # OVERRIDE
sourcedir = "."
books = [['Genesis', 'Genesis_First_Two']]
#tools.parseText("./Genesis_First_Two.xml", "Genesis", commentary_names, display=False)
#tools.parseText("./short.xml", "Genesis", commentary_names, display=False)
#tools.parseText("./Full_Berishit_OYW.xml", "Genesis", commentary_names, display=False)
#import sys; sys.exit()

for book in books:
	filekey = book[1]
	book_eng = book[0]
        file_with_path = sourcedir + "/" + filekey + ".xml"
	all_commentary = tools.parseText(file_with_path, book_eng, commentary_names, display=False)
        # Special category "Commentary" set in the sub
        extra_categories = ["Tanach", "Torah", book_eng]
        if not do_post:
                print "Not going to try to post", book_eng
                continue
        for commentary_name in all_commentary.keys():
                one_commentary = all_commentary[commentary_name]
                if tools.haveCommentaryRecord(server, commentary_name):
                        print commentary_name, "already has a commentary record"
                        try_post = True
                else:
                        # Returns false if create failed
                        # TODO Do I want a variant title?
                        commentary_name_and_variants = [commentary_name]
                        try_post = tools.createCommentaryRecord(server, api_key, commentary_name_and_variants, extra_categories)
                if not try_post:
                        print "Not trying to post the commentary text"
                        continue

                # Post text to server (not post-process text!)
                ref = "%s on %s" % (commentary_name, book_eng)
                tools.postText(server, api_key, ref, one_commentary)
	
