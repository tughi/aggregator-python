import "./EntryList.scss"

import classNames from "classnames"
import React, { useCallback, useRef } from "react"
import { ActionBar } from "./ActionBar"
import { useController } from "./Controller"
import { formatRelativeEntryTime } from "../utils/date"

export const EntryList = () => {
   const { activeEntryIndex, setActiveEntryIndex, setIsViewerVisible, setShowSideNav, refresh, session, toggleSortOrder, toggleMaxAge } = useController()
   const { isLoading, feedId, onlyStarred, latestFirst, maxAge, feedsById, entries, entriesLimit, hasMoreEntries, loadMoreEntries } = session

   const activeEntryCallback = useCallback(entryElement => {
      if (entryElement) {
         document.activeElement?.blur()
         entryElement.scrollIntoView({ behavior: 'smooth', block: 'nearest' })
      }
   }, [])

   const triggerEntryIndex = hasMoreEntries ? entries.length - Math.round(entriesLimit / 3) : -1
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

   return (
      <div className="EntryList content">
         <ActionBar>
            <ActionBar.Action icon="menu" onClick={() => setShowSideNav(showSideNav => !showSideNav)} />
            <ActionBar.Title>
               {feedId == null && !onlyStarred && "All"}
               {feedId == null && onlyStarred && "Starred"}
               {feedId && (feedsById[feedId]?.userTitle || feedsById[feedId]?.title)}
            </ActionBar.Title>
            <ActionBar.Count>
               {feedId == null && !onlyStarred && session.unreadEntries}
               {feedId == null && onlyStarred && session.starredEntries}
               {feedId && feedsById[feedId]?.unreadEntries}
            </ActionBar.Count>
            <ActionBar.Action icon={maxAge == null ? "calendar" : maxAge === 1 ? "calendar-day" : "calendar-week"} active={!!maxAge} onClick={toggleMaxAge} />
            <ActionBar.Action icon={latestFirst ? "sort-up" : "sort-down"} onClick={toggleSortOrder} />
            <ActionBar.Action icon="refresh" onClick={refresh} />
         </ActionBar>
         <div className="body">
            {entries.map((entry, entryIndex) => (
               <EntryItem
                  key={entry.id}
                  ref={entryIndex === triggerEntryIndex ? triggerEntryCallback : entryIndex === activeEntryIndex ? activeEntryCallback : null}
                  entry={entry}
                  feed={feedsById[entry.feedId]}
                  isActive={entryIndex === activeEntryIndex}
                  onClick={() => {
                     setActiveEntryIndex(entryIndex)
                     setIsViewerVisible(true)
                  }}
               />
            ))}
            {isLoading && (
               <div className="loading entry">
                  <div className="summary">
                     <div className="title">
                        Loading ...
                     </div>
                  </div>
               </div>
            )}
         </div>
      </div>
   )
}

const EntryItem = React.forwardRef(({ entry, feed, isActive, onClick }, ref) => {
   const { session } = useController()
   const { toggleEntryReadState } = session
   const onStateClick = useCallback(event => {
      event.stopPropagation()
      toggleEntryReadState(entry)
   }, [entry, toggleEntryReadState])
   return (
      <div className={classNames("entry", { unread: !entry.readTime, active: isActive })} ref={ref} >
         <div className="summary" onClick={onClick}>
            <a className="favicon" onClick={event => event.stopPropagation()} href={entry.link} target="_blank" rel="noopener noreferrer">
               {feed.faviconUrl ? (
                  <span className="image" style={{ backgroundImage: `url(${feed.faviconUrl})` }} />
               ) : (
                  <span className={`image rss-icon-${feed.id % 10/*sass:length($colors)*/ + 1}`} />
               )}
            </a>
            <div className="title">{entry.title}</div>
            <div className="date">{formatRelativeEntryTime(entry.publishTime)}</div>
            <button className={classNames("state", { pinned: entry.keepTime, done: entry.readTime })} onClick={onStateClick} />
         </div>
      </div>
   )
})
