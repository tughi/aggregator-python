import "./EntryViewer.scss"

import classNames from "classnames"
import { useCallback, useEffect, useRef } from "react"
import { ActionBar } from "./ActionBar"
import { useController } from "./Controller"
import { formatFullEntryTime } from "../utils/date"

export const EntryViewer = () => {
   const { activeEntryIndex, setActiveEntryIndex, isViewerVisible, setIsViewerVisible, session } = useController()
   const { feedsById, entryIds, entries, toggleEntryReadState, toggleEntryStarState } = session
   const entriesLength = entries.length

   const activeEntry = entries[activeEntryIndex]

   useEffect(() => {
      if (isViewerVisible && activeEntry && activeEntry.readTime == null && activeEntry.keepTime == null) {
         toggleEntryReadState(activeEntry)
      }
   }, [isViewerVisible, activeEntry, toggleEntryReadState])

   return (
      <div className={classNames("EntryViewer", "content", { active: isViewerVisible })}>
         <div className="header">
            <ActionBar>
               <ActionBar.Action icon="close" onClick={() => setIsViewerVisible(false)} />
               {activeEntry && (
                  <>
                     <ActionBar.Title>
                        {activeEntryIndex + 1} / {entryIds.length}
                     </ActionBar.Title>
                     <ActionBar.Action icon={activeEntry.starTime ? "star-on" : "star-off"} onClick={() => toggleEntryStarState(activeEntry)} />
                     <ActionBar.Action icon={activeEntry.keepTime ? "entry-pinned" : activeEntry.readTime ? "entry-done" : "entry-new"} active={!!activeEntry.keepTime} onClick={() => toggleEntryReadState(activeEntry)} />
                  </>
               )}
            </ActionBar>
         </div>
         <div className="body">
            {isViewerVisible && activeEntry && (
               <Entry entry={activeEntry} feed={feedsById[activeEntry.feedId]}>
                  <div className="entry-toolbar">
                     <button className="prev" onClick={() => setActiveEntryIndex(activeEntryIndex => Math.max(activeEntryIndex - 1, 0))} disabled={activeEntryIndex <= 0}>
                     </button>

                     <button className="next" onClick={() => setActiveEntryIndex(activeEntryIndex => Math.min(activeEntryIndex + 1, entriesLength - 1))} disabled={activeEntryIndex >= entriesLength - 1}>
                     </button>
                  </div>
               </Entry>
            )}
         </div>
      </div>
   )
}

const onLinkClick = event => {
   const element = event.target.closest('a')
   if (element) {
      event.preventDefault()
      const href = element.getAttribute('href')
      if (href) {
         window.open(href, '_blank', 'noopener noreferrer')
      }
   }
}

const Entry = ({ entry, feed, children }) => {
   const contentRef = useRef(null)
   const onContentRef = useCallback(node => {
      if (node) {
         node.addEventListener('click', onLinkClick)
      } else if (contentRef.current) {
         contentRef.current.removeEventListener('click', onLinkClick)
      }
      contentRef.current = node
   }, [])

   return (
      <div key={entry.id} className="entry">
         {entry && (
            <div ref={onContentRef} className="content">
               <div className="header">
                  <div className="source">
                     <span className="feed">{feed.userTitle || feed.title}</span>
                     {entry.author && (
                        <span className="author">{entry.author.name}</span>
                     )}
                  </div>
                  <h2><a className="title" href={entry.link}>{entry.title}</a></h2>
                  <div>
                     <span className="date" title={entry.publishText}>{formatFullEntryTime(entry.publishTime)}</span>
                  </div>
               </div>
               {((entry?.content.length && entry.content) || (entry.summary && [entry.summary]) || []).map((content, index) => (
                  <div key={index} dangerouslySetInnerHTML={{ __html: content.value }}></div>
               ))}
            </div>
         )}
         {children}
      </div>
   )
}
