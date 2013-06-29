var MONTH_NAMES = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];

function formatDate(date) {
    var day = date.getDate();
    var month = MONTH_NAMES[date.getMonth()];
    return month + ' ' + day;
}

function formatTime(date) {
    var hours = date.getHours();
    if (hours < 10) {
        hours = '0' + hours;
    }
    var minutes = date.getMinutes();
    if (minutes < 10) {
        minutes = '0' + minutes;
    }
    return hours + ':' + minutes;
}

function loadEntries() {
    var $entries = $("#entries").empty();

    var data = {};

    var hashMatch = /^#?(\d+)?(!(\d+))?/g.exec(window.location.hash);
    if (hashMatch[1]) {
        data['with_tags'] = hashMatch[1];
        data['without_tags'] = hashMatch[3] || 0;
    } else {
        data['without_tags'] = hashMatch[3] || 1;
    }

    $.ajax({
        url: "/api/entries",
        data: data,
        dataType: "json",
        success: function (data) {
            var currentDate = formatDate(new Date());
            var currentYear = new Date().getFullYear();

            $.each(data, function (index, entry) {
                var $entry = $entryTemplate.clone().appendTo("#entries");
                $entry.attr("id", entry.id);
                $entry.find("#entry-title").html(entry.title);
                $entry.find("#entry-link").attr("href", entry.link);

                if (entry.feed_favicon) {
                    $entry.find("#entry-link .favicon").css("background-image", "url('" + entry.feed_favicon + "')");
                }

                if (entry.content.length || entry.summary) {
                    $entry.data("content", entry.content.length ? entry.content : [entry.summary]);
                }

                var $entryDate = $entry.find("#entry-date");
                var entryTimestamp = new Date(entry.timestamp * 1000);
                var entryDate = formatDate(entryTimestamp);
                if (entryTimestamp.getFullYear() != currentYear) {
                    $entryDate.html(entryDate + ' ' + entryTimestamp.getFullYear());
                } else if (entryDate !== currentDate) {
                    $entryDate.html(entryDate);
                } else {
                    $entryDate.html(formatTime(entryTimestamp));
                }

                if ((entry.tags & 1) == 1) {
                    $entry.removeClass("unread");
                }

                if ((entry.tags & 2) == 2) {
                    $entry.find(".icon-star").removeClass("icon-white");
                }
            });
        }
    });
}

var $entryTemplate;

$(document).ready(function () {
    $entryTemplate = $("#entries > #entry-template").remove();

    loadEntries();
});

$(document).on("click", "#entries .accordion-toggle", function () {
    var $entry = $(this).closest(".accordion-group");
    $entry.addClass("active");
    $("#entries > .active").not($entry).removeClass("active");
    toggleEntry($entry);
    showEntry($entry)
});

$(document).on("click", "#entries .accordion-heading #entry-link", function (event) {
    event.stopPropagation();
});

$(document).on("click", "#entries .accordion-heading .icon-star", function (event) {
    event.stopPropagation();
    event.preventDefault();
    toggleStarredEntry($(this).closest(".accordion-group"));
});

function showEntry($entry) {
    if (!$entry.length) {
        // nothing to show
        return;
    }

    var $entriesScroller = $entry.closest("#entries-scroller");
    var scrollTop = $entriesScroller.scrollTop();
    var scrollBottom = scrollTop + $entriesScroller.height();
    var currentTop = $entry.position().top - $entry.parent().position().top;
    var currentBottom = currentTop + $entry.height();
    if (currentTop < scrollTop) {
        $entriesScroller.scrollTop(currentTop - 20);
    } else if (currentBottom > scrollBottom) {
        if ($entry.height() > $entriesScroller.height()) {
            $entriesScroller.scrollTop(currentTop - 20);
        } else {
            $entriesScroller.scrollTop(currentBottom - $entriesScroller.height() + 20);
        }
    }
}

function markReadEntry($entry, unread) {
    if (unread) {
        $entry.addClass("unread");
        untagEntry($entry, 1);
    } else {
        $entry.removeClass("unread");
        tagEntry($entry, 1);
    }
}

function tagEntry($entry, tag) {
    $.ajax({
        url: "/api/entries/" + $entry.attr("id") + "/tags",
        data: {
            tag: tag
        },
        method: "PUT",
        fail: function () {
            console.log("Failed to set tag " + tag + " on entry " + $entry.attr("id"));
        }
    });
}

function untagEntry($entry, tag) {
    $.ajax({
        url: "/api/entries/" + $entry.attr("id") + "/tags/" + tag,
        method: "DELETE",
        fail: function () {
            console.log("Failed to remove tag " + tag + " from entry: " + $entry.attr("id"));
        }
    });
}

function toggleStarredEntry($entry) {
    var $icon = $entry.find(".icon-star").toggleClass("icon-white");

    if ($icon.hasClass("icon-white")) {
        untagEntry($entry, 2);
    } else {
        tagEntry($entry, 2);
    }
}

function toggleEntry($entry) {
    if (!$entry.length) {
        // nothing to toggle
        return;
    }

    var $entryContent = $entry.find("#entry-content:empty");
    if ($entryContent.length) {
        var content = $entry.data("content");
        for (var key in content) {
            var value = content[key].value;
            $entryContent.append(value);
        }
    }

    $entry.toggleClass("open");
    $("#entries > .open").not($entry).removeClass("open").find("#entry-content").empty();
    markReadEntry($entry);
}

$(document).on("keydown", function (event) {
    var $activeEntry = $("#entries > .active");

    function nextEntry() {
        if ($activeEntry.length) {
            ($activeEntry = $activeEntry.next()).addClass("active").prev().removeClass("active");
        } else {
            $("#entries > :first-child").addClass("active");
        }
    }

    function prevEntry() {
        ($activeEntry = $activeEntry.prev()).addClass("active").next().removeClass("active");
    }

    switch (event.which) {
        case 74: // j
            nextEntry();
            toggleEntry($activeEntry);
            showEntry($activeEntry);
            break;
        case 75: // k
            prevEntry();
            toggleEntry($activeEntry);
            showEntry($activeEntry);
            break;
        case 77: // m
            markReadEntry($activeEntry, !$activeEntry.hasClass("unread"));
            break;
        case 78: // n
            nextEntry();
            showEntry($activeEntry);
            break;
        case 79: // o
            toggleEntry($activeEntry);
            showEntry($activeEntry);
            break;
        case 80: // p
            prevEntry();
            showEntry($activeEntry);
            break;
        case 82: // r
            loadEntries();
            break;
        case 83: // s
            toggleStarredEntry($activeEntry);
            break;
        case 86: // v
            window.open($activeEntry.find(".accordion-heading #entry-link").attr("href"));
            markReadEntry($activeEntry);
            break;
        default:
            console.log("unhandled keydown: " + event.which);
    }
});
