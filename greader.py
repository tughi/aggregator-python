import persistence
import opml


def import_outline(store, outline):
    try:
        if outline.type == 'rss':
            feed = persistence.Feed()
            feed.title = unicode(outline.title)
            feed.url = outline.xmlUrl
            store.add(feed)
    except AttributeError:
        if len(outline):
            for o in outline:
                import_outline(store, o)


if __name__ == '__main__':
    outlines = opml.parse('subscriptions.xml')

    store = persistence.open_store()

    import_outline(store, outlines)

    store.commit()
