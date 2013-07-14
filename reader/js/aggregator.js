$(function () {

    var Entry = Backbone.Model.extend({
    });

    var Entries = Backbone.Collection.extend({
        model: Entry,
        url: "/reader/entries"
    });

    var Session = Backbone.Model.extend({
        url: "/reader/session"
    });

    var EntriesView = Backbone.View.extend({
        el: $("#entries"),
        session: new Session,
        entries: new Entries,

        initialize: function () {
            this.$entryTemplate = this.$("> #entry-template").removeAttr("id").remove();

            this.listenTo(this.session, "change", this.refresh);
            this.listenTo(this.entries, "add", this.render);

            this.session.fetch();
        },

        refresh: function () {
            var entries = this.entries;
            entries.reset();

            this.now = moment();

            var page = new Entries;
            page.fetch({data: {ids: this.session.get("entries").slice(0, 50).join(",")}})
                .done(function () {
                    page.each(function (entry) {
                        entries.add(entry);
                    });
                });
        },

        render: function (entry) {
            var $entry = this.$entryTemplate.clone();

            $entry.find("#title").text(entry.get("title"));
            $entry.find("#favicon").attr("href", entry.get("link")).css("background-image", "url('" + "/favicon.ico" + "')");

            var date = moment(entry.get("updated"));
            var dateFormat = this.now.year() != date.year() ? "MMM DD YYYY" : this.now.date() != date.date() ? "MMM DD" : "hh:mm a";
            $entry.find("#date").text(date.format(dateFormat));

            this.$el.append($entry);
        }
    });

    new EntriesView();
});
