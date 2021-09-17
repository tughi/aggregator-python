import "./Reader.scss"

import React, { useCallback, useEffect, useMemo, useRef, useState } from "react"
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

const entriesLimit = 100

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
      return { sessionTime, feedId, onlyUnread, onlyStarred, entriesLimit }
   }, [match, sessionTime])

   const { isLoading, feeds, feedsById, entryIds, entries, unreadEntries, starredEntries, hasMoreEntries, loadMoreEntries } = useSession(sessionParams)
   const entriesLength = entries.length

   const [activeEntryIndex, setActiveEntryIndex] = useState(-1)
   const [showEntry, setShowEntry] = useState(false)

   useEffect(() => {
      setActiveEntryIndex(-1)
      setShowEntry(false)
   }, [entryIds])

   const activeEntryCallback = useCallback(entryElement => {
      if (entryElement) {
         entryElement.scrollIntoView({ behavior: 'smooth', block: 'center' })
      }
   }, [])

   const triggerEntryIndex = hasMoreEntries ? entriesLength - Math.round(entriesLimit / 3) : -1
   const triggerEntryObserver = useRef(null)
   const triggerEntryCallback = useCallback(entryElement => {
      if (isLoading) {
         return
      }
      if (triggerEntryObserver.current) {
         triggerEntryObserver.current.disconnect()
         triggerEntryObserver.current = null
      }
      if (entryElement) {
         triggerEntryObserver.current = new IntersectionObserver(observerEntries => {
            if (observerEntries[0].isIntersecting) {
               loadMoreEntries()
            }
         })
         triggerEntryObserver.current.observe(entryElement)
      }
   }, [isLoading, loadMoreEntries])

   useEffect(() => {
      const onKeyDown = event => {
         const key = event.which
         if (key === 66/*b*/ && activeEntryIndex !== -1) {
            // TODO: toggle bliss
         } else if (key === 74/*j*/ && entriesLength) {
            setActiveEntryIndex(Math.min(entriesLength - 1, activeEntryIndex + 1))
            setShowEntry(true)
         } else if (key === 75/*k*/ && entriesLength) {
            setActiveEntryIndex(Math.max(0, activeEntryIndex - 1))
            setShowEntry(true)
         } else if (key === 77/*m*/ && activeEntryIndex !== -1) {
            // TODO: toggle read/pinned
         } else if (key === 78/*n*/ && entriesLength) {
            setActiveEntryIndex(Math.min(entriesLength - 1, activeEntryIndex + 1))
         } else if (key === 79/*o*/ && activeEntryIndex !== -1) {
            setShowEntry(showEntry => !showEntry)
         } else if (key === 80/*p*/ && entriesLength) {
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
   }, [activeEntryIndex, entriesLength])

   const onFeedClick = useCallback(() => setSessionTime(Date.now()), [])

   return (
      <div className="Reader">
         <div className="side-nav">
            <div className="feeds">
               <FeedItem title="All" count={unreadEntries} link="/reader/all" active={match.path === "/reader/all"} onClick={onFeedClick} />
               <FeedItem title="Starred" count={starredEntries} link="/reader/starred" active={match.path === "/reader/starred"} onClick={onFeedClick} />
               <hr />
               {feeds.map(feed => (
                  <FeedItem key={feed.id} title={feed.userTitle || feed.title} count={feed.unreadEntries} link={`/reader/feeds/${feed.id}`} active={sessionParams.feedId === feed.id} onClick={onFeedClick} />
               ))}
            </div>
         </div>
         <div className="container">
            <div className="feed-view">
               <div className="entries">
                  {entries.map((entry, entryIndex) => (
                     <EntryItem
                        key={entry.id}
                        ref={entryIndex === triggerEntryIndex ? triggerEntryCallback : entryIndex === activeEntryIndex ? activeEntryCallback : null}
                        entry={entry}
                        feed={feedsById[entry.feedId]}
                        isActive={entryIndex === activeEntryIndex}
                        onClick={() => {
                           setActiveEntryIndex(entryIndex)
                           setShowEntry(true)
                        }}
                     />
                  ))}
                  {isLoading && (
                     <div style={{ textAlign: 'center' }}>
                        Loading...
                     </div>
                  )}
               </div>
            </div>
            {showEntry && entriesLength > activeEntryIndex && (
               <Entry entry={entries[activeEntryIndex]} feed={feedsById[entries[activeEntryIndex].feedId]} />
            )}
         </div>
      </div>
   )
}

const FeedItem = ({ title, count, active, link, onClick }) => (
   <Link className={classNames("feed", { active, hidden: !count })} to={link} onClick={onClick}>
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
