import { useMemo } from "react"
import { Link } from "react-router-dom"
import { useSession } from "./hooks/backend"

export const Reader = ({ match }) => {
   const sessionParams = useMemo(() => {
      let feedId = null
      let onlyUnread = true
      let onlyStarred = false
      if (match.path === '/reader/starred') {
         onlyUnread = false
         onlyStarred = true
      } else if (match.path === '/reader/feed/:feedId') {
         feedId = parseInt(match.params.feedId)
      }
      return { feedId, onlyUnread, onlyStarred, firstEntries: 50 }
   }, [match])

   const { session } = useSession(sessionParams)

   const allUnreadEntries = useMemo(() => {
      return session ? session.feeds.reduce((sum, feed) => sum + feed.unreadEntries, 0) : 0
   }, [session])

   return (
      <>
         {session && (
            <>
               <div className="FeedsView">
                  <FeedItem title="All" unreadEntries={allUnreadEntries} link="/reader/all" />
                  <FeedItem title="Starred" unreadEntries={0} link="/reader/starred" />
                  <hr />
                  {session.feeds.map(feed => (
                     <FeedItem key={feed.id} title={feed.userTitle || feed.title} unreadEntries={feed.unreadEntries} link={`/reader/feed/${feed.id}`} />
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
      </>
   )
}

const FeedItem = ({ title, unreadEntries, link }) => (
   <Link className="feed-item" to={link}>
      <span className="label text-body">{title}</span>
      {unreadEntries > 0 && (
         <span className="count text-secondary">{unreadEntries}</span>
      )}
   </Link>
)

const EntryItem = ({ entry }) => (
   <div className="entry-item">
      {entry.title}
   </div>
)
