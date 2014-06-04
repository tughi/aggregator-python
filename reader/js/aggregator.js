$(function () {

    var TAG_READ = 1;
    var TAG_STAR = 2;

    var Feed = Backbone.Model.extend({
        countAttr: 'unread',

        initialize: function () {
            this.set({route: '#read/feed/' + this.id});
        }
    });

    var AllFeed = Feed.extend({
        countAttr: 'count',

        initialize: function () {
            this.set({route: '#read'});
        },

        updateCount: function (feeds) {
            var count = 0;
            feeds.each(function (feed) {
                var unread = feed.get('unread');
                if (unread) {
                    count += unread;
                }
            });

            this.set({count: count});
        }
    });

    var StarredFeed = Feed.extend({
        initialize: function () {
            this.set({route: '#read/starred'});
        }
    });

    var Feeds = Backbone.Collection.extend({
        comparator: 'sortIndex',

        initialize: function () {
            this.listenTo(this, 'reset', this.onReset);
            this.listenTo(this, 'change:unread', this.onUnreadChanged);
        },

        onReset: function () {
            this.onUnreadChanged();
        },

        onUnreadChanged: function () {
            this.get('all').updateCount(this);
        }
    });

    var FeedView = Backbone.View.extend({
        tagName: 'div',
        className: 'feed',
        template: _.template($('#feed-template').text()),

        initialize: function () {
            this.listenTo(this.model, 'change', this.render);
        },

        render: function () {
            this.$el.html(this.template({feed: this.model}));
            this.$el.attr('id', this.model.id);

            this.$el.toggleClass('active', window.location.hash == this.model.get('route'));

            return this;
        }
    });

    var FeedsView = Backbone.View.extend({
        el: '#feeds',

        initialize: function () {
            this.listenTo(this.collection, 'reset', this.render);
        },

        render: function () {
            this.$el.empty();

            this.collection.each(function (feed) {
                new FeedView({model: feed}).render().$el.appendTo(this.$el);
            }.bind(this));
        }
    });

    var Entry = Backbone.Model.extend({
        initialize: function () {
            this.set({updated_text: this.formatDate(this.get('updated'))});
        },

        getFeed: function () {
            return window.reader.feeds.get(this.get('feed_id'));
        },

        isUnread: function () {
            return  (this.get('reader_tags') & TAG_READ) == 0;
        },

        isStarred: function () {
            return  (this.get('reader_tags') & TAG_STAR) == TAG_STAR;
        },

        formatDate: function (date) {
            var date = moment(date);
            var sessionDate = window.reader.session.date;

            if (sessionDate.year() != date.year()) {
                return date.format('MMM DD YYYY');
            }

            if (sessionDate.date() == date.date() && sessionDate.month() == date.month()) {
                return date.format('hh:mm a');
            }

            return date.format('MMM DD');
        },

        toggleTag: function (tag) {
            var reader_tags = this.get('reader_tags');
            var patched_reader_tags = reader_tags ^ tag;
            $.ajax({
                url: 'api/entries/' + this.id,
                method: 'PATCH',
                data: {
                    reader_tags: patched_reader_tags
                },
                success: function () {
                    // update entry
                    this.set('reader_tags', patched_reader_tags);

                    if (tag == TAG_READ) {
                        // update feed unread count
                        var feed = this.getFeed();
                        feed.set('unread', feed.get('unread') + ((patched_reader_tags & TAG_READ) == 0 ? 1 : -1));
                    }
                }.bind(this)
            });
        }
    });

    var Entries = Backbone.Collection.extend({
        model: Entry,
        url: 'api/entries'    });

    var EntryView = Backbone.View.extend({
        tagName: 'div',
        className: 'entry',
        template: _.template($('#entry-template').text()),

        initialize: function () {
            this.listenTo(this.model, 'change', this.render);
        },

        render: function () {
            this.$el.html(this.template({entry: this.model, feed: this.model.getFeed()}));
            this.$el.attr('id', this.model.id);

            this.$el.toggleClass('unread', this.model.isUnread());
            this.$el.toggleClass('starred', this.model.isStarred());

            this.$el.toggleClass('active', this.model.get('_active') == true);
            this.$el.toggleClass('open', this.model.get('_open') == true);

            return this;
        }
    });

    var EntriesView = Backbone.View.extend({
        el: '#entries',

        initialize: function () {
            this.listenTo(this.collection, 'reset', this.onCollectionReset);
            this.listenTo(this.collection, 'add', this.onCollectionAdd);
        },

        onCollectionReset: function () {
            this.$el.empty();
        },

        onCollectionAdd: function (entry) {
            new EntryView({model: entry}).render().$el.appendTo(this.$el);
        }
    });

    var SessionOptions = Backbone.Model.extend({
        defaults: {
            with_tags: undefined,
            without_tags: undefined,
            order: '<',
            feed_id: undefined
        }
    });

    var Session = Backbone.Model.extend({
        url: 'reader/session'
    });

    var ENTRIES_PER_PAGE = 50;
    var ENTRY_HEIGHT = 30;

    var Reader = Backbone.View.extend({
        el: document,
        $window: $(window),

        events: {
            'keydown': 'onKeyDown',
            'scroll': 'onScroll',
            'click #entries > .entry #toggle': 'onEntryToggleClicked',
            'click #entries > .entry #toggle-read': 'onEntryToggleReadClick',
            'click #entries > .entry #star': 'onEntryToggleStarClick',
            'click #entries > .entry > #body a': 'onEntryAnchorClick'
        },

        initialize: function () {
            this.sessionOptions = new SessionOptions();
            this.session = new Session();
            this.feeds = new Feeds();
            this.entries = new Entries();

            new FeedsView({collection: this.feeds});
            new EntriesView({collection: this.entries});

            // toggle reader mode
            this.$('body').addClass(navigator.userAgent.match(/Android|iPhone|iPad|iPod/i) ? 'mobile' : 'desktop');

            this.listenTo(this.sessionOptions, 'change', this.reload);
            this.listenTo(this.session, 'change', this.onSessionChanged);
        },

        onSessionChanged: function () {
            this.session.date = moment();
            this.activeEntry = -1;
            this.openedEntry = -1;

            // clear entries model
            this.entries.reset();

            // update feeds model
            var feeds = [
                new AllFeed({id: 'all', title: 'All items', sortIndex: 'all'}),
                new StarredFeed({id: 'starred', title: 'Starred items', sortIndex: 'starred'})
            ];
            _.each(this.session.get('feeds'), function (feed) {
                feeds.push(new Feed(feed).set({sortIndex: 'x_' + feed.title.toLowerCase()}));
            });
            this.feeds.reset(feeds);

            var sessionEntries = this.session.get('entries');
            if (sessionEntries && sessionEntries.length) {
                // fetch first entries
                this.entries.fetch({
                    data: {
                        ids: sessionEntries.slice(0, ENTRIES_PER_PAGE).join(',')
                    },
                    remove: false
                });
            }
        },

        reload: function () {
            this.session.unset('entries');
            this.session.fetch({data: this.sessionOptions.toJSON()});
        },

        onKeyDown: function (event) {
            switch (event.which) {
                case 74: // j
                    this.activateEntry(Math.min(this.entries.length - 1, this.activeEntry + 1));
                    this.openEntry(this.activeEntry);
                    break;
                case 75: // k
                    this.activateEntry(Math.max(this.activeEntry - 1, 0));
                    this.openEntry(this.activeEntry);
                    break;
                case 77: // m
                    if (this.activeEntry > -1) {
                        this.entries.at(this.activeEntry).toggleTag(TAG_READ);
                    }
                    break;
                case 78: // n
                    this.activateEntry(Math.min(this.entries.length - 1, this.activeEntry + 1));
                    this.scrollToActive();
                    break;
                case 79: // o
                    if (this.openedEntry == this.activeEntry) {
                        // close entry
                        this.openedEntry = -1;
                        this.entries.at(this.activeEntry).unset('_open');
                        this.scrollToActive();
                    } else {
                        this.openEntry(this.activeEntry);
                    }
                    break;
                case 80: // p
                    this.activateEntry(Math.max(this.activeEntry - 1, 0));
                    this.scrollToActive();
                    break;
                case 82: // r
                    if (!event.metaKey) {
                        this.reload();
                    }
                    break;
                case 83: // s
                    if (this.activeEntry > -1) {
                        this.entries.at(this.activeEntry).toggleTag(TAG_STAR);
                    }
                    break;
                case 86: // v
                    var href = this.entries.at(this.activeEntry).get('link');
                    if (href) {
                        window.open(href);
                    }
                    break;
                default:
                    console.log('unexpected keydown: ' + event.which);
            }
        },

        onEntryToggleClicked: function (event) {
            var index = $(event.target).closest('.entry').index();
            var entry =  this.entries.at(index);

            if (entry.get('_open')) {
                // close entry
                event.stopPropagation();

                var index = $(event.target).closest('.entry').index();
                this.openedEntry = -1;
                this.entries.at(index).unset('_open');
            } else {
                // open entry
                this.activateEntry(index);
                this.openEntry(index);
            }
        },

        onEntryToggleReadClick: function (event) {
            var index = $(event.target).closest('.entry').index();
            this.entries.at(index).toggleTag(TAG_READ);
        },

        onEntryToggleStarClick: function (event) {
            var index = $(event.target).closest('.entry').index();
            this.entries.at(index).toggleTag(TAG_STAR);
        },

        onEntryAnchorClick: function (event) {
            event.stopPropagation();
            event.preventDefault();

            var href = $(event.target).attr("href");
            if (href) {
                window.open(href);
            }
        },

        activateEntry: function (index) {
            if (this.activeEntry > -1) {
                // deactivate current entry
                this.entries.at(this.activeEntry).unset('_active');
            }

            this.activeEntry = index;

            // activate the requested entry
            this.entries.at(index).set('_active', true);
        },

        openEntry: function (index) {
            var preloadEntries = _.range(Math.max(index - 2, 0), Math.min(index + 4, this.entries.length));

            if (this.openedEntry > -1) {
                // close current entry
                this.entries.at(this.openedEntry).unset('_open');

                // unload far entries
                var loadedEntries = _.range(Math.max(this.openedEntry - 2, 0), Math.min(this.openedEntry + 4, this.entries.length));
                _.each(_.difference(loadedEntries, preloadEntries), function (index) {
                    this.entries.at(index).unset('_loaded');
                }.bind(this));
            } else {
            }


            this.openedEntry = index;

            _.each(preloadEntries, function (index) {
                var entry = this.entries.at(index);

                // preload entry
                var values = { _loaded: true };

                if (index == this.openedEntry) {
                    // open entry
                    values._open = true;

                    if (entry.isUnread()) {
                        // mark as unread
                        entry.toggleTag(TAG_READ);
                    }
                }

                this.entries.at(index).set(values);
            }.bind(this));

            this.scrollToActive();
        },

        scrollToActive: function () {
            var $entry = this.$('#entries > .entry.active');

            if ($entry.length) {
                var bodyScrollTop = this.$window.scrollTop();

                var entryTop = $entry.position().top;

                if (entryTop < bodyScrollTop) {
                    this.$window.scrollTop(entryTop);
                } else {
                    var windowHeight = $(window).height();
                    var entryHeight = $entry.height();

                    if (entryTop + entryHeight - bodyScrollTop > windowHeight) {
                        this.$window.scrollTop(entryTop - Math.max(windowHeight - entryHeight, 0));
                    }
                }
            }
        },

        onScroll: function () {
            if (this.entries.length < this.session.get('entries').length && this.$el.height() - this.$el.scrollTop() < ENTRIES_PER_PAGE * ENTRY_HEIGHT) {
                // fetch next page
                this.entries.fetch({
                    data: {
                        ids: this.session.get('entries').slice(this.entries.length, this.entries.length + ENTRIES_PER_PAGE).join(',')
                    },
                    remove: false
                });
            }
        }
    });

    window.reader = new Reader();

    var Router = Backbone.Router.extend({
        routes: {
            'read': 'read',
            'read/starred': 'readStarred',
            'read/feed/:feed_id': 'readFeed'
        },

        read: function () {
            window.reader.sessionOptions.set({
                with_tags: undefined,
                without_tags: TAG_READ,
                feed_id: undefined
            });
        },

        readStarred: function () {
            window.reader.sessionOptions.set({
                with_tags: TAG_STAR,
                without_tags: undefined,
                feed_id: undefined
            });
        },

        readFeed: function (feed_id) {
            window.reader.sessionOptions.set({
                with_tags: undefined,
                without_tags: TAG_READ,
                feed_id: feed_id
            });
        }
    });

    var router = new Router();

    if (!Backbone.history.start()) {
        router.navigate('read', {trigger: true});
    }

});
