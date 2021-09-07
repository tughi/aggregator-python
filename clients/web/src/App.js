import { useMemo, useState } from 'react'
import './App.scss'
import { useSession } from './hooks/backend'

export const App = () => {
   const [sessionParams, setSessionParams] = useState({
      feedId: null,
      onlyUnread: true,
      onlyStarred: false,
      firstEntries: 50,
   })

   const { session } = useSession(sessionParams)

   const allUnreadEntries = useMemo(() => {
      return session ? session.feeds.reduce((sum, feed) => sum + feed.unreadEntries, 0) : 0
   }, [session])

   return (
      <div className="App">
         {session && (
            <>
               <div className="FeedsView">
                  <FeedItem title="All" unreadEntries={allUnreadEntries} />
                  <FeedItem title="Starred" unreadEntries={0} />
                  <hr />
                  {session.feeds.map(feed => (
                     <FeedItem key={feed.id} title={feed.userTitle || feed.title} unreadEntries={feed.unreadEntries} onClick={() => setSessionParams({ ...sessionParams, feedId: feed.id })} />
                  ))}
               </div>
               <div className="FeedView">
                  {session.entries.map(entry => (
                     <EntryItem key={entry.id} entry={entry} />
                  ))}
               </div>
               <div className="EntryView" />
            </>
         )}
      </div>
   )
}

const FeedItem = ({ title, unreadEntries, onClick }) => (
   <div className="feed-item" onClick={onClick}>
      <span className="label text-body">{title}</span>
      {unreadEntries > 0 && (
         <span className="count text-secondary">{unreadEntries}</span>
      )}
   </div>
)

const EntryItem = ({ entry }) => (
   <div className="entry-item">
      {entry.title}
   </div>
)
