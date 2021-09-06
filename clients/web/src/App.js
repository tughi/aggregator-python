import { useMemo } from 'react'
import './App.scss'
import { useFeeds } from './hooks/backend'

export const App = () => {
   const { feeds } = useFeeds()

   const allUnreadEntries = useMemo(() => {
      return feeds.reduce((sum, feed) => sum + feed.unreadEntries, 0)
   }, [feeds])

   return (
      <div className="App">
         <div className="FeedsView">
            <div>
               <FeedItem title="All" unreadEntries={allUnreadEntries} />
               <FeedItem title="Starred" unreadEntries={0} />
               <hr />
               {feeds.map(feed => (
                  <FeedItem key={feed.id} title={feed.userTitle || feed.title} unreadEntries={feed.unreadEntries} />
               ))}
            </div>
         </div>
         <div className="FeedView" />
         <div className="EntryView" />
      </div>
   )
}

const FeedItem = ({ title, unreadEntries }) => (
   <div className="feed-item">
      <span className="label text-body">{title}</span>
      {unreadEntries > 0 && (
         <span className="count text-secondary">{unreadEntries}</span>
      )}
   </div>
)
