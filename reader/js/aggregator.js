$(function () {

    var Entry = Backbone.Model.extend({
    });

    var Entries = Backbone.Collection.extend({
        model: Entry,
        url: "/reader/entries"
    });

    var Session = Backbone.Model.extend({
        url: "/reader/session",

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
        }
    });

    var EntriesView = Backbone.View.extend({
        el: $("#entries"),
        $feeds: $("#feeds"),
        session: new Session,
        entries: new Entries,

        initialize: function () {
            var view = this;

            view.$feedTemplate = view.$feeds.children("#feed-template").removeAttr("id").remove();
            view.$entryTemplate = view.$("> #entry-template").removeAttr("id").remove();

            view.$loader = view.$("> #loader").click(function () {
                view.fetchNextPage();
            });

            view.listenTo(view.session, "change", view.refresh);
            view.listenTo(view.entries, "add", view.render);

            view.session.fetch();
        },

        refresh: function () {
            var view = this;

            view.$el.children(".entry").remove();
            view.currentPage = -1;
            view.entries.reset();

            view.now = moment();

            if (view.session.hasFeeds()) {
                view.$feeds.children(".feed").remove();

                _.each(view.session.get("feeds"), function (feed) {
                    var $feed = view.$feedTemplate.clone();

                    $feed.find("#title").text(feed["title"]);

                    var count = feed["count"];
                    if (count > 0) {
                        $feed.find("#count").show().text('(' + count + ')');
                    } else {
                        $feed.find("#count").hide().text(null);
                    }

                    view.$feeds.append($feed);
                });
            }

            if (view.session.hasEntries()) {
                // fetch first page
                view.fetchNextPage();
            }
        },

        fetchNextPage: function () {
            var PAGE_ENTRIES = 50;

            var view = this;
            var page = view.currentPage + 1;

            var entryIds = view.session.get("entries");

            if (page <= entryIds.length / PAGE_ENTRIES) {
                var pageEntries = new Entries;
                var pageEntryIds = entryIds.slice(page * PAGE_ENTRIES, Math.min((page + 1) * PAGE_ENTRIES, entryIds.length));
                var data = {
                    ids: pageEntryIds.join(",")
                };
                pageEntries.fetch({data: data})
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
            $entry.find("#favicon").attr("href", entry.get("link")).css("background-image", "url('" + view.session.get("feeds")[entry.get("feed_id")]["favicon"] + "')");

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
                var $body = $("body,html");
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

    var view = new EntriesView();

    $(document).on("keydown", function (event) {
        switch (event.which) {
            case 74: // j
                view.openNext();
                view.scrollToActive();
                break;
            case 75: // k
                view.openPrev();
                view.scrollToActive();
                break;
            case 77: // m
                view.toggleRead();
                break;
            case 78: // n
                view.activateNext();
                view.scrollToActive();
                break;
            case 79: // o
                var $entry = view.$el.children(".active");
                if ($entry.length) {
                    view.toggleOpen($entry);
                    view.scrollToActive();
                }
                break;
            case 80: // p
                view.activatePrev();
                view.scrollToActive();
                break;
            case 82: // r
                view.session.clear();
                view.session.fetch();
                break;
            case 83: // s
                view.toggleStar();
                break;
            case 86: // v
                // TODO: window.open($activeEntry.find(".accordion-heading #entry-link").attr("href"));
                // break;
            default:
                console.log("unhandled keydown: " + event.which);
        }
    });

});
