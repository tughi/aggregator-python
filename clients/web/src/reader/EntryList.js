import "./EntryList.scss"

import classNames from "classnames"
import React, { useCallback, useEffect, useRef } from "react"
import { formatRelativeEntryTime } from "../utils/date"
import { ENTRIES_LIMIT, useSessionContext } from "./Session"
import { useController } from "./Controller"
import { ActionBar } from "./ActionBar"

export const EntryList = () => {
   const { isLoading, feedId, onlyStarred, feedsById, entryIds, entries, hasMoreEntries, loadMoreEntries, refresh } = useSessionContext()
   const entriesLength = entries.length

   const { activeEntryIndex, setActiveEntryIndex, setShowEntry, setShowSideNav } = useController()

   useEffect(() => {
      setActiveEntryIndex(-1)
      setShowEntry(false)
   }, [entryIds, setActiveEntryIndex, setShowEntry])

   const activeEntryCallback = useCallback(entryElement => {
      if (entryElement) {
         entryElement.scrollIntoView({ behavior: 'smooth', block: 'nearest' })
      }
   }, [])

   const triggerEntryIndex = hasMoreEntries ? entriesLength - Math.round(ENTRIES_LIMIT / 3) : -1
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
               {feedId && feedsById[feedId]?.title}
            </ActionBar.Title>
            <ActionBar.Action icon="refresh" onClick={() => refresh()} />
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
   )
}

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
