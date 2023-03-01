import "./FeedList.scss"

import classNames from "classnames"
import { useController } from "./Controller"

export const FeedList = () => {
   const { session } = useController()

   return (
      <div className="FeedList">
         <FeedItem
            link="/reader/all"
            title="All"
            count={session.unreadEntries}
            active={session.feedId == null && !session.onlyStarred}
            sessionParams={{ feedId: null, onlyUnread: true, onlyStarred: false }}
         />
         <FeedItem
            link="/reader/starred"
            title="Starred"
            count={session.starredEntries}
            active={session.feedId == null && session.onlyStarred}
            sessionParams={{ feedId: null, onlyUnread: false, onlyStarred: true }}
         />
         <hr />
         {session.feeds.map(feed => (
            <FeedItem
               key={feed.id}
               link={`/reader/feeds/${feed.id}`}
               title={feed.userTitle || feed.title}
               count={feed.unreadEntries}
               active={session.feedId === feed.id}
               sessionParams={{ feedId: feed.id, onlyUnread: true, onlyStarred: false }}
            />
         ))}
      </div>
   )
}

const FeedItem = ({ link, title, count, active, sessionParams }) => {
   const { openFeed } = useController()

   const onClick = event => {
      event.preventDefault()
      openFeed(link, sessionParams)
   }

   return (
      <a className={classNames("feed", { active, hidden: !count && !active })} href={link} onClick={onClick}>
         <span className="title">{title}</span>
         {count > 0 && (
            <span className="count">{count}</span>
         )}
      </a>
   )
}
