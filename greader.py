import persistence
import opml


def import_outline(store, outline):
    print(outline)

    try:
        if outline.type == 'rss':
            feed = persistence.Feed()
            feed.name = unicode(outline.title)
            feed.url = outline.xmlUrl
            store.add(feed)
    except AttributeError:
        if len(outline):
            for o in outline:
                import_outline(store, o)


if __name__ == '__main__':
    outlines = opml.parse('subscriptions.xml')
    store = persistence.Store(persistence.database)

    import_outline(store, outlines)

    store.commit()
