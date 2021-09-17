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
   const [sessionTime, setSessionTime] = useState(() => Date.now())
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
      return { sessionTime, feedId, onlyUnread, onlyStarred }
   }, [match, sessionTime])

   const { session } = useSession(sessionParams)

   const feeds = useMemo(() => session.feeds.reduce((feeds, feed) => { feeds[feed.id] = feed; return feeds }, {}), [session])

   const [activeEntryIndex, setActiveEntryIndex] = useState(-1)
   const [showEntry, setShowEntry] = useState(false)

   useEffect(() => {
      setActiveEntryIndex(-1)
      setShowEntry(false)
   }, [session])

   const activeEntryCallback = useCallback(entryElement => {
      if (entryElement) {
         entryElement.scrollIntoView({ behavior: 'smooth', block: 'center' })
      }
   }, [])

   useEffect(() => {
      const onKeyDown = event => {
         const key = event.which
         if (key === 66/*b*/ && activeEntryIndex !== -1) {
            // TODO: toggle bliss
         } else if (key === 74/*j*/ && session.entries.length) {
            setActiveEntryIndex(Math.min(session.entries.length - 1, activeEntryIndex + 1))
            setShowEntry(true)
         } else if (key === 75/*k*/ && session.entries.length) {
            setActiveEntryIndex(Math.max(0, activeEntryIndex - 1))
            setShowEntry(true)
         } else if (key === 77/*m*/ && activeEntryIndex !== -1) {
            // TODO: toggle read/pinned
         } else if (key === 78/*n*/ && session.entries.length) {
            setActiveEntryIndex(Math.min(session.entries.length - 1, activeEntryIndex + 1))
         } else if (key === 79/*o*/ && activeEntryIndex !== -1) {
            setShowEntry(showEntry => !showEntry)
         } else if (key === 80/*p*/ && session.entries.length) {
            setActiveEntryIndex(Math.max(0, activeEntryIndex - 1))
         } else if (key === 82/*r*/) {
            setSessionTime(Date.now())
         } else if (key === 83/*s*/ && activeEntryIndex !== -1) {
            // TODO: toggle star
         }
      }

      window.addEventListener('keydown', onKeyDown)

      return () => {
         window.removeEventListener('keydown', onKeyDown)
      }
   }, [session, activeEntryIndex])

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
         <div className="container">
            <div className="feed-view">
               <div className="entries">
                  {session.entries.map((entry, entryIndex) => (
                     <EntryItem
                        key={entry.id}
                        ref={entryIndex === activeEntryIndex ? activeEntryCallback : null}
                        entry={entry}
                        feed={feeds[entry.feedId]}
                        isActive={entryIndex === activeEntryIndex}
                        onClick={() => {
                           setActiveEntryIndex(entryIndex)
                           setShowEntry(true)
                        }}
                     />
                  ))}
               </div>
            </div>
            {showEntry && session.entries.length > activeEntryIndex && (
               <Entry entry={session.entries[activeEntryIndex]} feed={feeds[session.entries[activeEntryIndex].feedId]} />
            )}
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

const EntryItem = React.forwardRef(({ entry, feed, isActive, onClick }, ref) => {
   return (
      <div className={classNames("entry", { unread: !entry.readTime, active: isActive })} ref={ref}>
         <div className="summary" onClick={onClick}>
            <a className="favicon" onClick={event => event.stopPropagation()} href={entry.link} target="_blank" rel="noreferrer">
               <span className="image" style={{ backgroundImage: `url(${feed.faviconUrl})` }} />
            </a>
            <div className="title">{entry.title}</div>
            <div className="date">{formatRelativeEntryTime(entry.publishTime)}</div>
         </div>
      </div>
   )
})

const Entry = ({ entry, feed }) => (
   <div className="entry">
      {entry && (
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
