import "./EntryPager.scss"

import { formatFullEntryTime } from "../utils/date"
import { useController } from "./Controller"
import { useSessionContext } from "./Session"
import classNames from "classnames"
import { ActionBar } from "./ActionBar"

export const EntryPager = () => {
   const { feedsById, entries, entryIds } = useSessionContext()
   const entriesLength = entries.length

   const { activeEntryIndex, setActiveEntryIndex, showEntry, setShowEntry } = useController()

   const activeEntry = entries[activeEntryIndex]

   return (
      <div className={classNames("EntryPager", "content", { active: showEntry })}>
         <div className="header">
            <ActionBar>
               <ActionBar.Action icon="close" onClick={() => setShowEntry(false)} />
               <ActionBar.Title>
                  {activeEntryIndex + 1} / {entriesLength} / {entryIds.length}
               </ActionBar.Title>
               <ActionBar.Action icon={activeEntry?.starTime ? "star-on" : "star-off"} />
               <ActionBar.Action icon={activeEntry?.readTime ? "entry-done" : "entry-new"} />
            </ActionBar>
         </div>
         <div className="body">
            {showEntry && activeEntry && (
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
