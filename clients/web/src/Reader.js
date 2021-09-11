import "./Reader.scss"

import { useMemo } from "react"
import { Link } from "react-router-dom"
import { useSession } from "./hooks/backend"
import classNames from "classnames"

const fullDateFormat = new Intl.DateTimeFormat(window.navigator.language, { year: 'numeric', month: 'short', day: '2-digit' })
const shortDateFormat = new Intl.DateTimeFormat(window.navigator.language, { month: 'short', day: '2-digit' })
const timeFormat = new Intl.DateTimeFormat(window.navigator.language, { hour: '2-digit', minute: '2-digit' })

export const Reader = ({ match }) => {
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
      return { feedId, onlyUnread, onlyStarred }
   }, [match])

   const { session } = useSession(sessionParams)

   const feeds = useMemo(() => session.feeds.reduce((feeds, feed) => { feeds[feed.id] = feed; return feeds }, {}), [session])

   const now = new Date()
   const formatEntryTime = entryTime => {
      const date = new Date(entryTime)
      if (now.getFullYear() !== date.getFullYear()) {
         return fullDateFormat.format(date)
      }
      if (now.getDate() === date.getDate() && now.getMonth() === date.getMonth()) {
         return timeFormat.format(date)
      }
      return shortDateFormat.format(date)
   }

   return (
      <div className="Reader">
         <div className="side-nav">
            <div className="feeds">
               <FeedItem title="All" active={match.path === "/reader/all"} count={session.unreadEntries} link="/reader/all" />
               <FeedItem title="Starred" active={match.path === "/reader/starred"} count={session.starredEntries} link="/reader/starred" />
               <hr />
               {session.feeds.map(feed => (
                  <FeedItem key={feed.id} active={sessionParams.feedId === feed.id} title={feed.userTitle || feed.title} count={feed.unreadEntries} link={`/reader/feeds/${feed.id}`} />
               ))}
            </div>
         </div>
         <div className="content">
            <div className="entries">
               {session.entries.map(entry => {
                  const feed = feeds[entry.feedId]
                  return (
                     <div className={classNames("entry", { unread: !entry.readTime })} key={entry.id}>
                        <a className="favicon" style={{ backgroundImage: `url(${feed.faviconUrl})` }} href={entry.link} target="_blank" rel="noreferrer" />
                        <div className="title">{entry.title}</div>
                        <div className="date">{formatEntryTime(entry.publishTime)}</div>
                     </div>
                  )
               })}
            </div>
         </div>
      </div>
   )
}

const FeedItem = ({ title, count, active, link }) => (
   <Link className={classNames("feed", { active, hidden: !count })} to={link}>
      <span className="title">{title}</span>
      {count > 0 && (
         <span className="count">{count}</span>
      )}
   </Link>
)
