$(function () {

    var Entry = Backbone.Model.extend({
    });

    var Entries = Backbone.Collection.extend({
        model: Entry,
        url: "/reader/entries"
    });

    var SessionOptions = Backbone.Model.extend({
        initialize: function () {
            var model = this;
        
            model.loadData();

            model.listenTo(this, "change", this.storeData);

            $(window).on("hashchange", function () {
                model.loadData();
            });
        },

        loadData: function () {
            var data = {};

            var hashMatch = /^#(\d+)?(!(\d+))?([<>])?(\|(\d+)?)?/g.exec(window.location.hash);

            if (hashMatch[1]) {
                data["with_tags"] = hashMatch[1];
                data["without_tags"] = hashMatch[3] || 0;
            } else {
                data["without_tags"] = hashMatch[3] || 1;
            }

            data["order"] = hashMatch[4] || '<';

            if (hashMatch[6]) {
                data["feed_id"] = hashMatch[6];
            }
            
            this.set("data", data);
        },

        storeData: function () {
            var data = this.get("data");
            var hash = "#";

            if ("with_tags" in data) {
                hash += data["with_tags"];
            }

            if ("without_tags" in data) {
                hash += "!" + data["without_tags"];
            }

            if ("order" in data) {
                hash += data["order"];
            }

            if ("feed_id" in data) {
                hash += "|" + data["feed_id"];
            }

            window.location.hash = hash;
        },
        
        setFeedId: function (feedId) {
            this.set("data", $.extend($.extend({}, this.get("data")), {feed_id: feedId}));
        }
    });

    var Session = Backbone.Model.extend({
        url: "/reader/session",
        options: new SessionOptions,

        initialize: function () {
            this.listenTo(this.options, "change", this.reload);
        },

        hasFeeds: function () {
            var feeds = this.get("feeds");
            if (feeds) {
                for (var key in feeds) {
                    return true;
                }
            }
            return false;
        },

        hasEntries: function () {
            var entries = this.get("entries");
            return entries && entries.length;
        },

        reload: function () {
            this.clear();
            this.fetch({data: this.options.get("data")});
        }
    });

    var session = new Session;

    var FeedsView = Backbone.View.extend({
        el: $("#feeds"),

        initialize: function () {
            var view = this;

            view.$feedTemplate = view.$("> #feed-template").removeAttr("id").remove();

            view.listenTo(session, "change", view.render);
        },

        render: function () {
            var view = this;

            if (session.hasFeeds()) {
                view.$el.children(".feed").remove();

                _.each(session.get("feeds"), function (feed) {
                    var $feed = view.$feedTemplate.clone();

                    $feed.find("#title").text(feed["title"]);

                    var count = feed["count"];
                    if (count > 0) {
                        $feed.find("#count").show().text("(" + count + ")");
                    } else {
                        $feed.find("#count").hide().text(null);
                    }

                    $feed.on("click", function () {
                        session.options.setFeedId(feed["id"]);
                    });

                    view.$el.append($feed);
                });
            }
        }
    });

    var EntriesView = Backbone.View.extend({
        el: $("#entries"),
        $feeds: $("#feeds"),
        entries: new Entries,

        initialize: function () {
            var view = this;

            view.$entryTemplate = view.$("> #entry-template").removeAttr("id").remove();

            view.$loader = view.$("> #loader").click(function () {
                view.fetchNextPage();
            });

            view.listenTo(session, "change", view.refresh);
            view.listenTo(view.entries, "add", view.render);
        },

        refresh: function () {
            var view = this;

            view.$el.children(".entry").remove();
            view.currentPage = -1;
            view.entries.reset();

            view.now = moment();

            if (session.hasEntries()) {
                // fetch first page
                view.fetchNextPage();
            }
        },

        fetchNextPage: function () {
            var PAGE_ENTRIES = 50;

            var view = this;
            var page = view.currentPage + 1;

            var entryIds = session.get("entries");

            if (page <= entryIds.length / PAGE_ENTRIES) {
                var pageEntries = new Entries;
                var pageEntryIds = entryIds.slice(page * PAGE_ENTRIES, Math.min((page + 1) * PAGE_ENTRIES, entryIds.length));
                pageEntries.fetch({data: {ids: pageEntryIds.join(",")}})
                    .done(function () {
                        pageEntries.each(function (entry) {
                            view.entries.add(entry);
                        });

                        view.currentPage = page;

                        if ((page + 1) * PAGE_ENTRIES > entryIds.length) {
                            // no more entries to load
                            view.$loader.hide();
                        } else {
                            view.$loader.show().text((entryIds.length - (page + 1) * PAGE_ENTRIES) + " more");
                        }
                    })
                    .fail(function (xhdr, message, error) {
                        throw error;
                    });
            }
        },

        render: function (entry) {
            var view = this;
            var $entry = view.$entryTemplate.clone();

            if (entry.get("content").length || entry.get("summary")) {
                $entry.data("content", entry.get("content").length ? entry.get("content") : [entry.get("summary")]);
            }

            $entry.attr("id", entry.get("id"));
            $entry.find("#title").text(entry.get("title"));
            $entry.find("#favicon").attr("href", entry.get("link")).css("background-image", "url('" + session.get("feeds")[entry.get("feed_id")]["favicon"] + "')");

            var date = moment(entry.get("updated"));
            var now = view.now;
            var dateFormat = now.year() != date.year() ? "MMM DD YYYY" : now.date() == date.date() && now.month() == date.month() ? "hh:mm a" : "MMM DD";
            $entry.find("#date").text(date.format(dateFormat));

            var tags = entry.get("tags");
            if ((tags & 1) == 0) {
                $entry.addClass("unread");
            }
            if ((tags & 2) == 2) {
                $entry.addClass("starred");
            }

            $entry.find("> #header > #toggle").click(function () {
                view.toggleOpen($entry);
                view.scrollToActive();
            });

            this.$loader.before($entry);
        },

        toggleOpen: function ($entry) {
            this.$el.children(".active").removeClass("active");
            this.$el.children(".open").not($entry).removeClass("open").find("#content").empty();
            $entry.addClass("active").toggleClass("open");

            var content = $entry.data("content");
            var $content = $entry.find("#content:empty");
            if (content && $content.length) {
                for (var index in content) {
                    $content.append(content[index].value);
                }
            }
        },

        activateNext: function () {
            var $activeEntry = this.$el.children(".active");
            var $nextEntry;

            if ($activeEntry.length) {
                $nextEntry = $activeEntry.next(".entry");
                if (!$nextEntry.length) {
                    // already the last entry

                    this.fetchNextPage();

                    return $activeEntry;
                }
                $activeEntry.removeClass("active");
            } else {
                $nextEntry = this.$el.children(".entry:first");
            }

            $nextEntry.addClass("active");
            return $nextEntry;
        },

        activatePrev: function () {
            var $activeEntry = this.$el.children(".active");

            if ($activeEntry.length) {
                var $prevEntry = $activeEntry.prev(".entry");
                if ($prevEntry.length) {
                    $activeEntry.removeClass("active");
                    $prevEntry.addClass("active");

                    return $prevEntry;
                }
            }

            return $activeEntry;
        },

        openNext: function () {
            var $activeEntry = this.activateNext();

            this.$el.children(".open").not($activeEntry).removeClass("open");

            if (!$activeEntry.hasClass("open")) {
                this.toggleOpen($activeEntry);
            }
        },

        openPrev: function () {
            var $activeEntry = this.activatePrev();

            this.$el.children(".open").not($activeEntry).removeClass("open");

            if (!$activeEntry.hasClass("open")) {
                this.toggleOpen($activeEntry);
            }
        },

        scrollToActive: function () {
            var $entry = this.$el.children(".active");

            if ($entry.length) {
                var $body = $("body");
                var bodyScrollTop = $body.scrollTop();

                var entryTop = $entry.position().top;

                if (entryTop < bodyScrollTop) {
                    $body.scrollTop(entryTop - 4);
                } else {
                    var windowHeight = $(window).height();
                    var entryHeight = $entry.height();

                    if (entryTop + entryHeight - bodyScrollTop > windowHeight) {
                        $body.scrollTop(entryTop - 4 - Math.max(windowHeight - entryHeight - 8, 0));
                    }
                }
            }
        }
    });

    var feedsView = new FeedsView();
    var entriesView = new EntriesView();

    // load session
    session.reload();

    $(document).on("keydown", function (event) {
        switch (event.which) {
            case 74: // j
                entriesView.openNext();
                entriesView.scrollToActive();
                break;
            case 75: // k
                entriesView.openPrev();
                entriesView.scrollToActive();
                break;
            case 77: // m
                entriesView.toggleRead();
                break;
            case 78: // n
                entriesView.activateNext();
                entriesView.scrollToActive();
                break;
            case 79: // o
                var $entry = entriesView.$el.children(".active");
                if ($entry.length) {
                    entriesView.toggleOpen($entry);
                    entriesView.scrollToActive();
                }
                break;
            case 80: // p
                entriesView.activatePrev();
                entriesView.scrollToActive();
                break;
            case 82: // r
                session.reload();
                break;
            case 83: // s
                entriesView.toggleStar();
                break;
            case 86: // v
                // TODO: window.open($activeEntry.find(".accordion-heading #entry-link").attr("href"));
                // break;
            default:
                console.log("unhandled keydown: " + event.which);
        }
    });

});
