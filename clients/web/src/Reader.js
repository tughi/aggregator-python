import "./Reader.scss"

import React, { useCallback, useEffect, useMemo, useState } from "react"
import { Link } from "react-router-dom"
import { useSession } from "./hooks/backend"
import classNames from "classnames"

const fullDateFormat = new Intl.DateTimeFormat(window.navigator.language, { year: 'numeric', month: 'short', day: '2-digit' })
const shortDateFormat = new Intl.DateTimeFormat(window.navigator.language, { month: 'short', day: '2-digit' })
const timeFormat = new Intl.DateTimeFormat(window.navigator.language, { hour: '2-digit', minute: '2-digit' })

const formatRelativeEntryTime = (entryTime) => {
   const now = new Date()
   const date = new Date(entryTime)
   if (now.getFullYear() !== date.getFullYear()) {
      return fullDateFormat.format(date)
   }
   if (now.getDate() === date.getDate() && now.getMonth() === date.getMonth()) {
      return timeFormat.format(date)
   }
   return shortDateFormat.format(date)
}

const dateTimeFormat = new Intl.DateTimeFormat(window.navigator.language, { year: 'numeric', month: 'short', day: '2-digit', hour: '2-digit', minute: '2-digit', weekday: 'short' })

const formatFullEntryTime = (entryTime) => {
   const date = new Date(entryTime)
   return dateTimeFormat.format(date)
}

export const Reader = ({ match }) => {
   const sessionParams = useMemo(() => {
      let feedId = null
      let onlyUnread = true
      let onlyStarred = false
      if (match.path === '/reader/starred') {
         onlyUnread = false
         onlyStarred = true
      } else if (match.path === '/reader/feeds/:feedId') {
         feedId = parseInt(match.params.feedId)
      }
      return { feedId, onlyUnread, onlyStarred }
   }, [match])

   const { session } = useSession(sessionParams)

   const feeds = useMemo(() => session.feeds.reduce((feeds, feed) => { feeds[feed.id] = feed; return feeds }, {}), [session])

   const [openEntryIndex, setOpenEntryIndex] = useState(null)
   useEffect(() => setOpenEntryIndex(null), [session])
   const openEntryCallback = useCallback(entryElement => {
      if (entryElement) {
         entryElement.scrollIntoView()
      }
   }, [])

   return (
      <div className="Reader">
         <div className="side-nav">
            <div className="feeds">
               <FeedItem title="All" count={session.unreadEntries} link="/reader/all" active={match.path === "/reader/all"} />
               <FeedItem title="Starred" count={session.starredEntries} link="/reader/starred" active={match.path === "/reader/starred"} />
               <hr />
               {session.feeds.map(feed => (
                  <FeedItem key={feed.id} title={feed.userTitle || feed.title} count={feed.unreadEntries} link={`/reader/feeds/${feed.id}`} active={sessionParams.feedId === feed.id} />
               ))}
            </div>
         </div>
         <div className="content">
            <div className="entries">
               {session.entries.map((entry, entryIndex) => (
                  <EntryItem
                     key={entry.id}
                     ref={entryIndex === openEntryIndex ? openEntryCallback : null}
                     entry={entry}
                     feed={feeds[entry.feedId]}
                     toggle={() => setOpenEntryIndex(current => current !== entryIndex ? entryIndex : null)}
                     isOpen={entryIndex === openEntryIndex}
                     hasContent={openEntryIndex !== null && entryIndex >= Math.max(openEntryIndex - 2, 0) && entryIndex <= openEntryIndex + 2}
                  />
               ))}
            </div>
         </div>
      </div>
   )
}

const FeedItem = ({ title, count, active, link }) => (
   <Link className={classNames("feed", { active, hidden: !count })} to={link}>
      <span className="title">{title}</span>
      {count > 0 && (
         <span className="count">{count}</span>
      )}
   </Link>
)

const EntryItem = React.forwardRef(({ entry, feed, toggle, isOpen, hasContent }, ref) => {
   return (
      <div className={classNames("entry", { unread: !entry.readTime, open: isOpen })} ref={ref}>
         <div className="summary" onClick={toggle}>
            <a className="favicon" onClick={event => event.stopPropagation()} href={entry.link} target="_blank" rel="noreferrer">
               <span className="image" style={{ backgroundImage: `url(${feed.faviconUrl})` }} />
            </a>
            <div className="title">{entry.title}</div>
            <div className="date">{formatRelativeEntryTime(entry.publishTime)}</div>
         </div>
         {hasContent && (
            <div className="content">
               <div className="header">
                  <div className="source">
                     <span className="feed">{feed.userTitle || feed.title}</span>
                     {entry.author && (
                        <span className="author">{entry.author.name}</span>
                     )}
                  </div>
                  <h2><a className="title" href={entry.link} target="_blank" rel="noreferrer">{entry.title}</a></h2>
                  <div>
                     <span className="date" title={entry.publishText}>{formatFullEntryTime(entry.publishTime)}</span>
                  </div>
               </div>
               {((entry?.content.length && entry.content) || (entry.summary && [entry.summary]) || []).map((content, index) => (
                  <div key={index} dangerouslySetInnerHTML={{ __html: content.value }}></div>
               ))}
            </div>
         )}
      </div>
   )
})
