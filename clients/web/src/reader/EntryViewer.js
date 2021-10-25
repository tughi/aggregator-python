import "./EntryViewer.scss"

import classNames from "classnames"
import { useEffect } from "react"
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

const Entry = ({ entry, feed, children }) => (
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
      {children}
   </div>
)
