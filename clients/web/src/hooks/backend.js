import axios from "axios"
import { useCallback, useEffect, useMemo, useState } from "react"

const useQuery = ({ query, variables, consumeData }) => {
   const [loading, setLoading] = useState(false)

   useEffect(() => {
      let cancelRequest

      setLoading(true)

      axios({
         url: '/graphql',
         method: 'post',
         data: { query, variables },
         cancelToken: new axios.CancelToken(cancel => cancelRequest = cancel)
      }).then(response => {
         setLoading(false)
         consumeData(response.data.data)
      }).catch(error => {
         if (axios.isCancel(error)) {
            return
         }
      })

      return () => {
         cancelRequest()
      }
   }, [query, variables, consumeData])

   return loading
}

export const useSession = ({ sessionTime, feedId, onlyUnread, onlyStarred, entriesLimit = 50 }) => {
   const variables = useMemo(() => {
      if (sessionTime) {
         return { feedId, onlyUnread, onlyStarred, entriesLimit }
      }
   }, [sessionTime, feedId, onlyUnread, onlyStarred, entriesLimit])

   const [feeds, setFeeds] = useState([])
   const [feedsById, setFeedsById] = useState({})
   const [unreadEntries, setUnreadEntries] = useState(0)
   const [starredEntries, setStarredEntries] = useState(0)
   const [entryIds, setEntryIds] = useState([])
   const [entries, setEntries] = useState([])

   useEffect(() => {
      setEntryIds([])
      setEntries([])
   }, [variables])

   const consumeSessionData = useCallback(({ session }) => {
      setFeeds(session.feeds)
      setFeedsById(session.feeds.reduce((feedsById, feed) => ({ ...feedsById, [feed.id]: feed })))
      setUnreadEntries(session.unreadEntries)
      setStarredEntries(session.starredEntries)
      setEntryIds(session.entryIds)
      setEntries(session.entries)
   }, [])

   const loading = useQuery({
      query: `query ($feedId: Int, $onlyUnread: Boolean, $onlyStarred: Boolean, $entriesLimit: Int!) {
         session(feedId: $feedId, onlyUnread: $onlyUnread, onlyStarred: $onlyStarred) {
            entries(limit: $entriesLimit) {
               id
               feedId
               title
               link
               summary { value }
               content { value }
               author { name }
               publishText
               publishTime
               readTime
               starTime
            }
            entryIds
            feeds {
               id
               faviconUrl
               title
               userTitle
               unreadEntries
            }
            unreadEntries
            starredEntries
         }
      }`,
      variables,
      consumeData: consumeSessionData,
   })

   return {
      loading,
      feeds,
      feedsById,
      entryIds,
      entries,
      unreadEntries,
      starredEntries,
   }
}
