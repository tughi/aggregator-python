$(function () {

    $("body").addClass(navigator.userAgent.match(/Android|iPhone|iPad|iPod/i) ? "mobile" : "desktop");

    var TAG_READ = 1;
    var TAG_STAR = 2;

    var Entry = Backbone.Model.extend({
    });

    var Entries = Backbone.Collection.extend({
        model: Entry,
        url: "/api/entries"
    });

    var SessionOptions = Backbone.Model.extend({
        initialize: function () {
            var model = this;

            model.listenTo(model, "change", model.storeData);

            $(window).on("hashchange", function () {
                model.loadData();
            });
        },

        loadData: function () {
            var values = {
                without_tags: TAG_READ,
                order: "<"
            };

            var hashMatch = /^#(\d+)?(!(\d+))?([<>])(\|(\d+))?/g.exec(window.location.hash);

            if (hashMatch) {
                if (hashMatch[1]) {
                    values["with_tags"] = hashMatch[1];
                    values["without_tags"] = hashMatch[3] || null;
                } else {
                    values["with_tags"] = null;
                    values["without_tags"] = hashMatch[3];
                }

                values["order"] = hashMatch[4];

                values["feed_id"] = hashMatch[6] || null;
            }

            this.set(values);
        },

        storeData: function () {
            var hash = "#";

            var with_tags = this.get("with_tags");
            if (with_tags) {
                hash += with_tags;
            }

            var without_tags = this.get("without_tags");
            if (without_tags) {
                hash += "!" + without_tags;
            }

            var order = this.get("order");
            if (order) {
                hash += order;
            }

            var feed_id = this.get("feed_id");
            if (feed_id) {
                hash += "|" + feed_id;
            }

            window.location.hash = hash;
        }
    });

    var Session = Backbone.Model.extend({
        url: "/reader/session",
        options: new SessionOptions,

        initialize: function () {
            this.listenTo(this.options, "change", this.reload);

            this.options.loadData();
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
            var options = this.options.toJSON();
            for (var key in options) {
                if (options[key] == null) {
                    delete options[key];
                }
            }

            this.clear();
            this.fetch({data: options});
        }
    });

    var session = new Session;

    var FeedsView = Backbone.View.extend({
        el: $("#feeds"),

        initialize: function () {
            var view = this;

            view.$feedTemplate = view.$("> #feed-template").removeAttr("id").remove();

            view.$el.children("#all").on("click", function () {
                session.options.set({"with_tags": null, "without_tags": TAG_READ, "feed_id": null});
            });

            view.$el.children("#starred").on("click", function () {
                session.options.set({"with_tags": TAG_STAR, "without_tags": null, "feed_id": null});
            });

            view.listenTo(session, "change", view.render);
        },

        render: function () {
            var view = this;

            if (session.hasFeeds()) {
                view.$("> .feed").not("#all,#starred").remove();

                var feeds = session.get("feeds");
                var sortedFeeds = [];
                for (var id in feeds) {
                    var feed = feeds[id];
                    sortedFeeds.push([feed["title"].toLowerCase(), feed]);
                }
                sortedFeeds.sort();

                var totalCount = 0;

                for (var index in sortedFeeds) {
                    var feed = sortedFeeds[index][1];
                    var $feed = view.$feedTemplate.clone();

                    $feed.attr("id", feed["id"]);
                    $feed.find("#title").text(feed["title"]);

                    var count = feed["count"];
                    $feed.find("#count").text(count > 0 ? count : "");

                    if (count == 0) {
                        $feed.addClass("read");
                    }

                    $feed.on("click", function () {
                        session.options.set({"with_tags": null, "without_tags": TAG_READ, "feed_id": $(this).attr("id")});
                    });

                    view.$el.append($feed);
                    totalCount += count;
                }

                view.$("> #all #count").text(totalCount > 0 ? totalCount : "");

                var sessionFeedId = session.options.get("feed_id");
                if (sessionFeedId) {
                    view.$("> #" + sessionFeedId).addClass("active");
                }
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

            var tags = entry.get("reader_tags") | entry.get("server_tags");
            if ((tags & TAG_READ) == 0) {
                $entry.addClass("unread");
            }
            if ((tags & TAG_STAR) == TAG_STAR) {
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

            var entry = this.entries.get($entry.attr("id"));
            var reader_tags = entry.get("reader_tags");
            var patched_reader_tags = reader_tags | TAG_READ;
            if (reader_tags != patched_reader_tags) {
                $.ajax({
                    url: "/api/entries/" + entry.id,
                    method: "PATCH",
                    data: {
                        reader_tags: patched_reader_tags
                    },
                    success: function () {
                        entry.set("reader_tags", patched_reader_tags);
                        $entry.removeClass("unread");
                    }
                });
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
        },

        toggleTag: function (tag, $entry) {
            $entry = $entry || this.$el.children(".active");

            if ($entry.length) {
                var entry = this.entries.get($entry.attr("id"));
                var reader_tags = entry.get("reader_tags");
                var patched_reader_tags = reader_tags ^ tag;
                var server_tags = entry.get("server_tags");
                if ((patched_reader_tags | server_tags) != (reader_tags | server_tags)) {
                    $.ajax({
                        url: "/api/entries/" + entry.id,
                        method: "PATCH",
                        data: {
                            reader_tags: patched_reader_tags
                        },
                        success: function () {
                            entry.set("reader_tags", patched_reader_tags);

                            if ((patched_reader_tags & TAG_READ) == TAG_READ) {
                                $entry.removeClass("unread");
                            } else {
                                $entry.addClass("unread");
                            }

                            if ((patched_reader_tags & TAG_STAR) == TAG_STAR) {
                                $entry.addClass("starred");
                            } else {
                                $entry.removeClass("starred");
                            }
                        }
                    });
                }
            }
        }
    });

    var feedsView = new FeedsView();
    var entriesView = new EntriesView();

    $(document).on("click", "#entries > .entry > #header > #star", function (event) {
        event.stopPropagation();
        event.preventDefault();

        entriesView.toggleTag(TAG_STAR, $(this).closest(".entry"));
    });

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
                entriesView.toggleTag(TAG_READ);
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
                entriesView.toggleTag(TAG_STAR);
                break;
            case 86: // v
                var href = entriesView.$("> .active.entry > #header > #favicon").attr("href");
                if (href) {
                    window.open(href);
                }
                break;
            default:
                console.log("unhandled keydown: " + event.which);
        }
    });

});
