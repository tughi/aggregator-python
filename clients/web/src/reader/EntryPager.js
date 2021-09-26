import "./EntryPager.scss"
import { ReactComponent as NextIcon } from "../icons/next.svg"
import { ReactComponent as PrevIcon } from "../icons/prev.svg"

import { formatFullEntryTime } from "../utils/date"
import { useController } from "./Controller"
import { useSessionContext } from "./Session"

export const EntryPager = () => {
   const { feedsById, entries } = useSessionContext()
   const entriesLength = entries.length

   const { activeEntryIndex, setActiveEntryIndex, showEntry } = useController()

   return (
      <div className="EntryPager">
         {showEntry && entriesLength > activeEntryIndex && (
            <Entry entry={entries[activeEntryIndex]} feed={feedsById[entries[activeEntryIndex].feedId]}>
               <div className="entry-toolbar">
                  <button className="prev" onClick={() => setActiveEntryIndex(activeEntryIndex => Math.max(activeEntryIndex - 1, 0))} disabled={activeEntryIndex <= 0}>
                     <PrevIcon />
                  </button>

                  <div className="actions">
                     <button className="star">S</button>
                     <div className="text">{activeEntryIndex + 1} / {entriesLength}</div>
                     <button className="pin">P</button>
                  </div>

                  <button className="next" onClick={() => setActiveEntryIndex(activeEntryIndex => Math.min(activeEntryIndex + 1, entriesLength - 1))} disabled={activeEntryIndex >= entriesLength - 1}>
                     <NextIcon />
                  </button>
               </div>
            </Entry>
         )}
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
