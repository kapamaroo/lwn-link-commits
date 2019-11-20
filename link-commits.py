#!/usr/bin/python3

import os
import sys
import git
import lxml.html
import lxml.etree
import urllib.parse
import urllib.request
from lxml.html.soupparser import unescape

linux_repo_path = "/opt/src/linux"
tags_cache = "tags.cache"
origpage = "page.html"
testpage = "testpage.html"
default_url = "https://lwn.net/Articles/804262/"

def normalize_tags(tags):
    tags = [ l.strip('\'').split(',') for l in tags ]
    tags = [ l.lstrip().rstrip() for t in tags for l in t ]
    tags = list(filter(lambda l: l.startswith("tag: "), tags))
    tags = [ l.split()[1] for l in tags ]

    return tags

def create_git_db(linux_repo_path, to_version):

    linux_repo = git.Git(linux_repo_path)

    if not os.path.isfile(tags_cache):
        print("init", tags_cache)
        tags = linux_repo.log("--simplify-by-decoration", "--no-merges", "--pretty=format:'%D'")
        tags = normalize_tags(tags.splitlines())

        with open(tags_cache, "w") as f:
            for l in tags:
                print(l, file=f)
    else:
        print("read", tags_cache)
        with open(tags_cache, "r") as f:
            tags = f.read().splitlines()

    if not to_version.startswith('v'):
        to_version = 'v' + to_version

    if to_version == tags[-1]:
        from_version = to_version
    else:
        try:
            idx = tags.index(to_version)
        except:
            print("update", tags_cache)
            new_tags = linux_repo.log("--simplify-by-decoration", "%s.." %(tags[0]), "--no-merges", "--pretty=format:'%D'")
            new_tags = normalize_tags(new_tags.splitlines())

            tags = new_tags + tags

            with open(tags_cache, "w") as f:
                for l in tags:
                    print(l, file=f)

            idx = tags.index(to_version)

        from_version = tags[idx + 1]

    print("get commits %s..%s" %(from_version, to_version))
    db  = linux_repo.log("%s..%s" %(from_version, to_version), "--no-merges", "--pretty=format:%H %s")
    db = [ [ l.split()[0], " ".join(l.split()[1:]) ] for l in db.splitlines() ]

    return db

def get_commit(db, msg):
    for l in db:
        if l[1].startswith(msg):
            return l[0]
        if l[1].startswith(unescape(msg)):
            return l[0]
    return None

def get_link(db, msg):
    commit = msg.strip(' ').rstrip(' ')
    ucommit = urllib.parse.quote(commit)

    search_link = 'https://git.kernel.org/pub/scm/linux/kernel/git/torvalds/linux.git/log/?qt=grep&q='
    direct_link = "https://git.kernel.org/pub/scm/linux/kernel/git/torvalds/linux.git/commit/?id="

    try:
        hcommit = get_commit(db, commit)
        if hcommit:
            # print(hcommit, commit)
            final_link = direct_link + hcommit
        else:
            print("warning: commit: %s" %(commit))
            final_link = search_link + ucommit
    except Exception as e:
        print(e)
        print("error: commit: %s" %(commit))
        final_link = search_link + ucommit

    ret = "    <a href=\"%s\">%s</a>" %(final_link, commit)

    return ret

def get_content(page):
    req = urllib.request.Request(page)
    with urllib.request.urlopen(req) as response:
        content = response.read()
        content = content.decode("utf-8")

    return content

def do_link_commits(db, body_str):
    lines = body_str.splitlines()
    new_lines = []

    print("link commits ...")

    for i, line in enumerate(lines, 1):
        new_lines.append(line)
        if line == "---":
            break

    lines = lines[i:]
    for i, line in enumerate(lines, i):
        if line.startswith(' '):
            new_text = get_link(db, line)
            new_lines.append(new_text)
        else:
            new_lines.append(line)

    new_lines[0] = "\n<pre>"
    new_lines.append("</pre>\n\n")

    new_body_str = "\n".join(new_lines)

    return new_body_str

def link_commits(page):
    print("page: %s" %(page))

    content = get_content(page)
    root = lxml.etree.HTML(content)

    with open(origpage, "w") as f:
        print(lxml.etree.tostring(root, encoding='unicode', method="html"), file=f)

    body = root.xpath("//div[contains(@class, 'ArticleText')]")[0]
    article = body.xpath("//pre//text()")[0]
    h1 = root.xpath("//h1//text()")[0]
    to_version = h1.split()[1]

    db = create_git_db(linux_repo_path, to_version)

    new_article = lxml.html.fromstring(do_link_commits(db, str(article)))
    article.getparent().getparent().replace(article.getparent(), new_article)

    print("generate", testpage)
    with open(testpage, "w") as f:
        print("<!DOCTYPE HTML PUBLIC \"-//W3C//DTD HTML 4.01 Transitional//EN\"", file=f)
        print("        \"http://www.w3.org/TR/html4/loose.dtd\">", file=f)
        print("        ", end='', file=f)
        print(lxml.etree.tostring(root, encoding='unicode', method="html"), file=f)

if __name__ == "__main__":
    if len(sys.argv) == 1:
        print("expected url argument, continue with default url\n")
        page = default_url
    else:
        page = sys.argv[1]

    link_commits(page)
