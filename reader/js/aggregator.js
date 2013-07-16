$(function () {

    var Entry = Backbone.Model.extend({
    });

    var Entries = Backbone.Collection.extend({
        model: Entry,
        url: "/reader/entries"
    });

    var Session = Backbone.Model.extend({
        url: "/reader/session",

        hasEntries: function () {
            var entries = this.get("entries");
            return entries && entries.length;
        }
    });

    var EntriesView = Backbone.View.extend({
        el: $("#entries"),
        session: new Session,
        entries: new Entries,

        initialize: function () {
            var view = this;

            view.$entryTemplate = this.$("> #entry-template").removeAttr("id").remove();

            view.$loader = view.$("> #loader").click(function () {
                view.fetchNextPage();
            });

            view.listenTo(this.session, "change", view.refresh);
            view.listenTo(this.entries, "add", view.render);

            view.session.fetch();
        },

        refresh: function () {
            this.currentPage = -1;
            this.entries.reset();

            this.now = moment();

            if (this.session.hasEntries()) {
                // fetch first page
                this.fetchNextPage();
            }
        },

        fetchNextPage: function () {
            var PAGE_ENTRIES = 50;

            var view = this;
            var page = view.currentPage + 1;

            var entryIds = view.session.get("entries");

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
                    }
                });
        },

        render: function (entry) {
            var $entry = this.$entryTemplate.clone();

            $entry.find("#title").text(entry.get("title"));
            $entry.find("#favicon").attr("href", entry.get("link")).css("background-image", "url('" + "/favicon.ico" + "')");

            var date = moment(entry.get("updated"));
            var dateFormat = this.now.year() != date.year() ? "MMM DD YYYY" : this.now.date() == date.date() && this.now.month() == date.month() ? "hh:mm a" : "MMM DD";
            $entry.find("#date").text(date.format(dateFormat));

            this.$loader.before($entry);
        }
    });

    new EntriesView();
});
