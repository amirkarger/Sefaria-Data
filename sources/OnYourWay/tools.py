# -*- coding: utf-8 -*-

# Parsing OnYourWay documents

import urllib
import urllib2
from urllib2 import URLError, HTTPError
import json
import os
import re
import array
from bs4 import BeautifulSoup
import sys

#sourcedir = "."
OYW_website="http://tora.ws"
#OYW_unicode_colon = u"\u05c3"

def readApiKey(api_key_file):
        f = open(api_key_file)
        api_key = f.readline().strip()
        f.close()
        return api_key

def soup(filename):
        f = open(filename, "r")
        page = f.read()
        f.close()
        return BeautifulSoup(page)

# The text we build a json of will have:
# * array of chapters, each of which has...
# * array of verses in a chapter, each of which has...
# * array of comments on each verse for a given commentary (or [])
def parseText(file_with_path, book_eng, commentary_number_to_name, display=False):
        # Force just doing one commentary...
        #commentary_number_to_name = { 7:	commentary_number_to_name[7], }

	s = soup(file_with_path)
        books = s.find_all("book")
        book = s.book
        book_heb = book['n']

        # Figure out which parshanim are in this text
        # Create an output file for each
        parshan_id_tags = book.find_all("pid")
        print "Commentaries for %s aka %s (with OnYourWay pids):" % (book_heb, book_eng)
        all_comments = dict() # actual comment data
        comment_count = dict() # total comments for a commentary in whole book
        for pidtag in parshan_id_tags:
            pid = int(pidtag['n'])
            # Maybe only getting a subset of commentaries
            if not commentary_number_to_name.has_key(pid):
                continue
            commentary_name = commentary_number_to_name[pid]
            print "\t%s (%d)" % (commentary_name, pid)
            all_comments[commentary_name] = []
            comment_count[commentary_name] = 0
        commentary_names_to_parse = all_comments.keys()

        # Read a chapter at at a time
        chapter_tags = s.find_all("chap")
        print "%d chapters" % len(chapter_tags)
        chapter_count = 0 # XXX is this always true?
        for chap in chapter_tags:
            chapter_count += 1
            commentary_chapter = dict()
            for commentary_name in commentary_names_to_parse:
                commentary_chapter[commentary_name] = []
            chapter_heb_num = chap['n']
            verses = chap.find_all("p", recursive=False)
            print chapter_heb_num + " %d psukim" % len(verses)

            verse_heb_nums = []
            verse_count = 0
            for verse in verses:
                verse_heb_num = verse['n']
                verse_count += 1
                first = verse_heb_num[0]
                last = verse_heb_num[-1]
                if first != "{":
                    print "Expecting { as first char in verse num, '%s'" % verse_heb_num
                if last != "}":
                    print "Expecting } as last char in verse num, '%s'" % verse_heb_num
                if first == "{" and last == "}":
                    verse_heb_num = verse_heb_num[1:-1]
                verse_heb_nums.append(verse_heb_num)

                verse_text = verse.d.text.strip()
                #if display:
                #    print book_heb, chapter_count, verse_count, verse_text.strip(OYW_unicode_colon)

                # Returns key = commentary name, value = list of comments
                commentary_verse = parse_one_verse_commentaries(
                    verse, commentary_number_to_name, 
                    chapter_heb_num, verse_heb_num, display
                )

                # When you finish a verse, add each commentary for that verse
                # to that commentary's chapter
                for commentary_name in commentary_names_to_parse:
                    if commentary_verse.has_key(commentary_name):
                        verse_comm = commentary_verse[commentary_name]
                    else:
                        verse_comm = []
                    commentary_chapter[commentary_name].append(verse_comm)
                    if len(verse_comm):
                        comment_count[commentary_name] += len(verse_comm)
                        if display:
                            print chapter_heb_num, verse_heb_num, len(verse_comm), commentary_name

            # End of chapter
            for commentary_name in commentary_names_to_parse:
                commentary_verses = commentary_chapter[commentary_name] 
                one_chapter_commentary = {
                    'chapter_heb_num':          chapter_heb_num,
                    'chapter_count':            chapter_count,
                    'verses':                   commentary_verses
                }
                # All we upload is the verses
                all_comments[commentary_name].append(commentary_verses)
            #print " ".join(verse_heb_nums)

        # Done with the book
        # Create a json for each commentary
        all_commentary_objects = dict() # metadata plus all_comments, per perush
        for commentary_name in commentary_names_to_parse:
            conr = "%s on %s" % (commentary_name, book_eng)
            one_count = comment_count[commentary_name]
            if one_count == 0:
                print "Skipping %s, which has no comments on %s" % (commentary_name, book_eng)
                continue

            print "%s has %d comments on %s" % (commentary_name, one_count, book_eng)
            one_whole_commentary = {
                    "versionTitle": conr,
                    "versionSource": OYW_website,
                    "language": "he",
                    "commentaryBook": book_eng,
                    "text": all_comments[commentary_name]
            }
		
            f = open("json/" + conr + ".json", "w")
            json.dump(one_whole_commentary, f)
            f.close()
            all_commentary_objects[commentary_name] = one_whole_commentary

	return all_commentary_objects


def parse_one_verse_commentaries(
        verse, commentary_number_to_name, 
        chapter_heb_num, verse_heb_num, display=False
):
        commentary_verse = dict()
        # Commentaries that actually comment on this verse...
        commentaries = verse.find_all("t")
        for comm_tag in commentaries:
            comm_num = int(comm_tag['i'])
            if not commentary_number_to_name.has_key(comm_num):
                continue
            commentary_name = commentary_number_to_name[comm_num]
            commentary_text = comm_tag.text

            # There may be multiple comments in a verse
            # OYW decorates deebur hamatchil with a <b>
            # Hopefully there aren't other <b>s!
            # But some perushim (like onkelos) don't have any DH

            # TODO <small>
            #    * small+small used in perushim for mareh mkomot
            #    * Other places seem to have span+small
            #    * Also small used to add edits like [et]
            # <b> and <small> tags in commentary text
            # aren't parsed out because they're in a CDATA (I think)
            # so re-BeautifulSoup the little piece of text
            comments = ['']
            found_bold = False
            bsct = BeautifulSoup(commentary_text)

            #print commentary_name
            # TODO rashi Breishit 49:26 may have weird XML in it
            for child in bsct.children:
                # Deebur hamatchil
                if child.name == "b":
                    # There might be text before the first DH, or no DH at all.
                    # All text before OR after first <b> goes into first comment
                    # but if you have a *second* DH, it becomes a new comment
                    if found_bold:
                        comments.append('')
                    comments[-1] += child.get_text()
                    found_bold = True
                # br's. E.g., Ramban 49:33
                elif child.name == "br":
                    comments[-1] += "\\n"
                    #print comments[-1]
                # Regular old string
                elif not hasattr(child, "text"):
                    comments[-1] += child
                # Something else
                # TODO (someday): search strings in parens for references
                # to other locations in Tanach, Talmud, etc.
                else:
                    comments[-1] += child.text

            # Get rid of \r\n at the end, any weird beginning spaces
            commentary_verse[commentary_name] = [c.strip() for c in comments]
        return commentary_verse

# return whether commentary record exists"
def haveCommentaryRecord(server, commentary_name):
        print "Testing whether %s has a commentary record" % commentary_name
	url = 'http://' + server + '/api/index/' + commentary_name.replace(" ", "_")
	req = urllib2.Request(url)
	try:
		response = urllib2.urlopen(req)
                response_text = response.read()
		print "Response is ", response_text
                # If "Unknown text" is in the string, we do NOT have a record
                found = response_text.find("Unknown text") != -1;
                return not found
	except HTTPError, e:
		print 'Error code: ', e.code
		print e.read()
                print "Giving up since we can't even do a GET from %s" % server
                sys.exit()

# Return True if we managed to create the record
def createCommentaryRecord(server, apikey, commentary_name_and_variants, extra_categories, oldTitle=''):
        commentary_name = commentary_name_and_variants[0]
        print "Creating commentary record for", commentary_name
        # NOTE! Commentary must be the *first* category.
        # Then Sefaria recognizes we're sending in a commentary
        # and we don't have to make a separate book record for each
        # book that that commentary comments on (because Sefaria combines
        # the overall commentary record with the book-being-commented-on record)
        categories = ["Commentary", ] + extra_categories
	index = {
		"title": commentary_name,
		"titleVariants": commentary_name_and_variants,
		"sectionNames": ["Chapter", "Verse", "Comment"],
		"categories": categories,
	}

	if(oldTitle):
		index['oldTitle'] = oldTitle

	url = 'http://' + server + '/api/index/' + index["title"].replace(" ", "_")
	indexJSON = json.dumps(index)
        print indexJSON
	values = {
		'json': indexJSON, 
		'apikey': apikey
	}
	data = urllib.urlencode(values)
	print url, data
	req = urllib2.Request(url, data)
	try:
		response = urllib2.urlopen(req)
		print response.read()
                return True
	except HTTPError, e:
		print 'Error code: ', e.code
                print e.read()
                return False



def postText(server, apikey, ref, text):
	textJSON = json.dumps(text)
	ref = ref.replace(" ", "_")
        # count_after=0, index_after=0 speeds up uploading
        # and lets those steps happen in batch later
	url = 'http://' + server + '/api/texts/%s?count_after=0&index_after=0' % ref
	print url
	values = {
		'json': textJSON, 
		'apikey': apikey
	}
	data = urllib.urlencode(values)
	req = urllib2.Request(url, data)
	try:
		response = urllib2.urlopen(req)
		print response.read()
	except HTTPError, e:
		print 'Error code: ', e.code
		print e.read()
		
