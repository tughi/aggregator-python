import axios from "axios"
import { useEffect, useMemo, useState } from "react"

const useQuery = (query, { variables }) => {
   const [loading, setLoading] = useState(false)
   const [data, setData] = useState(null)

   useEffect(() => {
      let cancelRequest

      setLoading(true)

      axios({
         url: '/graphql',
         method: 'post',
         data: { query, variables },
         cancelToken: new axios.CancelToken(cancel => cancelRequest = cancel)
      }).then(response => {
         setData(response.data.data)
         setLoading(false)
      }).catch(error => {
         if (axios.isCancel(error)) {
            return
         }
      })

      return () => {
         cancelRequest()
      }
   }, [query, variables])

   return { loading, data }
}

export const useSession = ({ feedId, onlyUnread, onlyStarred, entriesLimit = 50 }) => {
   const variables = useMemo(() => ({ feedId, onlyUnread, onlyStarred, entriesLimit }), [feedId, onlyUnread, onlyStarred, entriesLimit])

   const { loading, data } = useQuery(
      `query ($feedId: Int, $onlyUnread: Boolean, $onlyStarred: Boolean, $entriesLimit: Int!) {
         session(feedId: $feedId, onlyUnread: $onlyUnread, onlyStarred: $onlyStarred) {
            entries(limit: $entriesLimit) {
               id
               feedId
               title
               link
               summary { value }
               content { value }
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
      { variables },
   )

   return { loading, session: data?.session }
}
